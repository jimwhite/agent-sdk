"""Event handling for ACP server."""

import logging
from typing import TYPE_CHECKING

from acp import SessionNotification
from acp.schema import (
    ContentBlock1,
    ContentBlock2,
    SessionUpdate2,
    SessionUpdate4,
    SessionUpdate5,
    ToolCallContent1,
)

from openhands.agent_server.pub_sub import Subscriber
from openhands.sdk import ImageContent, TextContent
from openhands.sdk.event.base import LLMConvertibleEvent
from openhands.sdk.event.llm_convertible.action import ActionEvent
from openhands.sdk.event.llm_convertible.observation import (
    AgentErrorEvent,
    ObservationEvent,
    UserRejectObservation,
)

from .utils import get_tool_kind


if TYPE_CHECKING:
    from acp import AgentSideConnection

logger = logging.getLogger(__name__)


class EventSubscriber(Subscriber):
    """Subscriber for handling OpenHands events and converting them to ACP
    notifications."""

    def __init__(self, session_id: str, conn: "AgentSideConnection"):
        """Initialize the event subscriber.

        Args:
            session_id: The ACP session ID
            conn: The ACP connection for sending notifications
        """
        self.session_id = session_id
        self.conn = conn

    async def __call__(self, event):
        """Handle incoming events and convert them to ACP notifications."""
        # Handle different event types
        if isinstance(event, ActionEvent):
            await self._handle_action_event(event)
        elif isinstance(
            event, (ObservationEvent, UserRejectObservation, AgentErrorEvent)
        ):
            await self._handle_observation_event(event)
        elif isinstance(event, LLMConvertibleEvent):
            await self._handle_llm_convertible_event(event)

    async def _handle_action_event(self, event: ActionEvent):
        """Handle ActionEvent by sending tool_call notification."""
        try:
            tool_kind = get_tool_kind(event.tool_name)

            # Create a human-readable title
            action_name = event.action.__class__.__name__
            title = f"{action_name} with {event.tool_name}"

            # Extract thought content as text
            thought_text = " ".join([t.text for t in event.thought])

            await self.conn.sessionUpdate(
                SessionNotification(
                    sessionId=self.session_id,
                    update=SessionUpdate4(
                        sessionUpdate="tool_call",
                        toolCallId=event.tool_call_id,
                        title=title,
                        kind=tool_kind,
                        status="pending",
                        content=[
                            ToolCallContent1(
                                type="content",
                                content=ContentBlock1(
                                    type="text",
                                    text=thought_text
                                    if thought_text.strip()
                                    else f"Executing {action_name}",
                                ),
                            )
                        ]
                        if thought_text.strip()
                        else None,
                        rawInput=event.tool_call.function.arguments
                        if hasattr(event.tool_call.function, "arguments")
                        else None,
                    ),
                )
            )
        except Exception as e:
            logger.debug(f"Error processing ActionEvent: {e}")

    async def _handle_observation_event(
        self, event: ObservationEvent | UserRejectObservation | AgentErrorEvent
    ):
        """Handle observation events by sending tool_call_update notification."""
        try:
            if isinstance(event, ObservationEvent):
                # Successful tool execution
                status = "completed"
                # Extract content from observation
                content_parts = []
                for item in event.observation.agent_observation:
                    if isinstance(item, TextContent):
                        content_parts.append(item.text)
                    elif hasattr(item, "text") and not isinstance(item, ImageContent):
                        content_parts.append(getattr(item, "text"))
                    else:
                        content_parts.append(str(item))
                content_text = "".join(content_parts)
            elif isinstance(event, UserRejectObservation):
                # User rejected the action
                status = "failed"
                content_text = f"User rejected: {event.rejection_reason}"
            else:  # AgentErrorEvent
                # Agent error
                status = "failed"
                content_text = f"Error: {event.error}"

            await self.conn.sessionUpdate(
                SessionNotification(
                    sessionId=self.session_id,
                    update=SessionUpdate5(
                        sessionUpdate="tool_call_update",
                        toolCallId=event.tool_call_id,
                        status=status,
                        content=[
                            ToolCallContent1(
                                type="content",
                                content=ContentBlock1(
                                    type="text",
                                    text=content_text,
                                ),
                            )
                        ]
                        if content_text.strip()
                        else None,
                        rawOutput={"result": content_text}
                        if content_text.strip()
                        else None,
                    ),
                )
            )
        except Exception as e:
            logger.debug(f"Error processing observation event: {e}")

    async def _handle_llm_convertible_event(self, event: LLMConvertibleEvent):
        """Handle other LLMConvertibleEvent events."""
        try:
            llm_message = event.to_llm_message()

            # Send the event as a session update
            if llm_message.role == "assistant":
                # Send all content items from the LLM message
                for content_item in llm_message.content:
                    if isinstance(content_item, TextContent):
                        if content_item.text.strip():
                            # Send text content
                            await self.conn.sessionUpdate(
                                SessionNotification(
                                    sessionId=self.session_id,
                                    update=SessionUpdate2(
                                        sessionUpdate="agent_message_chunk",
                                        content=ContentBlock1(
                                            type="text",
                                            text=content_item.text,
                                        ),
                                    ),
                                )
                            )
                    elif isinstance(content_item, ImageContent):
                        # Send each image URL as separate content
                        for image_url in content_item.image_urls:
                            # Determine if it's a URI or base64 data
                            is_uri = image_url.startswith(("http://", "https://"))
                            await self.conn.sessionUpdate(
                                SessionNotification(
                                    sessionId=self.session_id,
                                    update=SessionUpdate2(
                                        sessionUpdate="agent_message_chunk",
                                        content=ContentBlock2(
                                            type="image",
                                            data=image_url,
                                            mimeType="image/png",
                                            uri=image_url if is_uri else None,
                                        ),
                                    ),
                                )
                            )
                    elif isinstance(content_item, str):
                        if content_item.strip():
                            # Send string content as text
                            await self.conn.sessionUpdate(
                                SessionNotification(
                                    sessionId=self.session_id,
                                    update=SessionUpdate2(
                                        sessionUpdate="agent_message_chunk",
                                        content=ContentBlock1(
                                            type="text",
                                            text=content_item,
                                        ),
                                    ),
                                )
                            )
        except Exception as e:
            logger.debug(f"Error processing LLMConvertibleEvent: {e}")
