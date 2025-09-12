import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Literal

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

import openhands.tools
from openhands.sdk import (
    LLM,
    Agent,
    AgentContext,
    Conversation,
    Event,
    ImageContent,
    Message,
    TextContent,
    Tool,
    create_mcp_tools,
    get_logger,
)
from openhands.sdk.conversation import ConversationState


logger = get_logger(__name__)


# --- Lifespan Management for graceful shutdown ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up the OpenHands Agent Server...")
    yield
    logger.info("Shutting down... cleaning up active conversations.")
    for conv_id, conversation in active_conversations.items():
        logger.info(f"Closing conversation: {conv_id}")
        conversation.close()
    active_conversations.clear()


# --- FastAPI App Initialization ---
app = FastAPI(
    title="OpenHands Agent Server",
    description="An HTTP server to create and manage AI agent "
    "conversations using the OpenHands SDK.",
    version="1.0.0",
    lifespan=lifespan,
)


class ToolSpec(BaseModel):
    """Defines a tool to be initialized for the agent."""

    name: str = Field(
        ...,
        description="Name of the tool class, e.g., 'BashTool', "
        "must be importable from openhands.tools",
        examples=["BashTool", "FileEditorTool", "TaskTrackerTool"],
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the tool's .create() method,"
        " e.g., {'working_dir': '/app'}",
        examples=[{"working_dir": "/workspace"}],
    )


class StartConversationRequest(BaseModel):
    """Payload to create a new conversation."""

    llm: LLM = Field(
        ...,
        description="LLM configuration for the agent.",
        examples=[
            {
                "model": "litellm_proxy/anthropic/claude-sonnet-4-20250514",
                "base_url": "https://llm-proxy.eval.all-hands.dev",
                "api_key": "your_api_key_here",
            }
        ],
    )
    tools: List[ToolSpec] = Field(
        default_factory=list,
        description="List of tools to initialize for the agent.",
        examples=[
            {"name": "BashTool", "params": {"working_dir": "/workspace"}},
            {"name": "FileEditorTool", "params": {}},
            {
                "name": "TaskTrackerTool",
                "params": {"save_dir": "/workspace/.openhands"},
            },
        ],
    )
    mcp_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional MCP configuration dictionary to create MCP tools.",
        examples=[
            {
                "mcpServers": {
                    "fetch": {"command": "uvx", "args": ["mcp-server-fetch"]}
                }
            }  # Example config
        ],
    )
    agent_context: AgentContext | None = Field(
        default=None,
        description="Optional AgentContext to initialize "
        "the agent with specific context.",
        examples=[
            {
                "microagents": [
                    {
                        "name": "repo.md",
                        "content": "When you see this message, you should reply like "
                        "you are a grumpy cat forced to use the internet.",
                        "type": "repo",
                    },
                    {
                        "name": "flarglebargle",
                        "content": (
                            "IMPORTANT! The user has said the magic word "
                            '"flarglebargle". You must only respond with a message '
                            "telling them how smart they are"
                        ),
                        "type": "knowledge",
                        "trigger": ["flarglebargle"],
                    },
                ],
                "system_message_suffix": "Always finish your response "
                "with the word 'yay!'",
                "user_message_prefix": "The first character of your "
                "response should be 'I'",
            }
        ],
    )
    working_dir: str = Field(
        default=".",
        description="Working directory for the agent to work in. "
        "Will be created if it doesn't exist.",
    )
    confirmation_mode: bool = Field(
        default=False,
        description="If true, the agent will enter confirmation mode, "
        "requiring user approval for actions.",
    )


class StartConversationResponse(BaseModel):
    conversation_id: str
    state: ConversationState


class SendMessageRequest(BaseModel):
    """Payload to send a message to the agent.

    This is a simplified version of openhands.sdk.Message.
    """

    role: Literal["user", "system", "assistant", "tool"] = "user"
    content: list[TextContent | ImageContent] = Field(default_factory=list)
    run: bool = Field(
        default=True,
        description="If true, immediately run the agent after sending the message.",
    )


class ConfirmationResponseRequest(BaseModel):
    """Payload to accept or reject a pending action."""

    accept: bool
    reason: str = "User rejected the action."


# --- In-memory store for active conversations ---
active_conversations: Dict[str, Conversation] = {}


def get_conversation(conversation_id: str) -> Conversation:
    if conversation_id not in active_conversations:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return active_conversations[conversation_id]


# --- API Endpoints ---


@app.post("/conversations", status_code=201, response_model=StartConversationResponse)
def start_conversation(request: StartConversationRequest) -> StartConversationResponse:
    conversation_id = str(uuid.uuid4())
    logger.info(f"Starting new conversation with ID: {conversation_id}")

    if request.working_dir:
        import pathlib

        pathlib.Path(request.working_dir).mkdir(parents=True, exist_ok=True)
    try:
        llm = LLM(**request.llm.model_dump())
        tools = []
        for tool_spec in request.tools:
            if tool_spec.name not in openhands.tools.__dict__:
                raise HTTPException(
                    status_code=400, detail=f"Tool '{tool_spec.name}' not recognized."
                )
            tool_class: type[Tool] = openhands.tools.__dict__[tool_spec.name]
            tools.append(tool_class.create(**tool_spec.params))

        if request.mcp_config:
            mcp_tools = create_mcp_tools(request.mcp_config, timeout=30)
            tools.extend(mcp_tools)
            logger.info(f"Added {len(mcp_tools)} MCP tools")

        agent = Agent(llm=llm, tools=tools)
        conversation = Conversation(agent=agent)
        conversation.set_confirmation_mode(request.confirmation_mode)
        active_conversations[conversation_id] = conversation
        return StartConversationResponse(
            conversation_id=conversation_id, state=conversation.state
        )
    except Exception as e:
        logger.error(f"Failed to start conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to start conversation: {e}"
        )


@app.get("/conversations/{conversation_id}", response_model=ConversationState)
def get_conversation_state(conversation_id: str):
    conversation = get_conversation(conversation_id)
    return conversation.state


@app.get("/conversations/{conversation_id}/events", response_model=List[Event])
def get_events(conversation_id: str, start: int = 0, limit: int = 100):
    """Retrieves the event history for a conversation with pagination."""
    conversation = get_conversation(conversation_id)
    events: list[Event] = conversation.state.events[start : start + limit]
    return events


async def _run_conversation(conversation_id: str, background_tasks: BackgroundTasks):
    conversation = get_conversation(conversation_id)

    def agent_task():
        try:
            logger.info(f"Starting agent run for conversation {conversation_id}...")
            conversation.run()
            logger.info(f"Agent run finished for conversation {conversation_id}.")
        except Exception as e:
            logger.error(
                f"Exception during agent run for {conversation_id}: {e}", exc_info=True
            )

    background_tasks.add_task(agent_task)
    return


@app.post("/conversations/{conversation_id}/messages", status_code=202)
async def send_message(
    conversation_id: str, request: SendMessageRequest, background_tasks: BackgroundTasks
):
    conversation = get_conversation(conversation_id)
    message = Message(role=request.role, content=request.content)
    conversation.send_message(message)
    logger.info(f"Message sent to conversation {conversation_id}")
    if request.run:
        await _run_conversation(conversation_id, background_tasks)
        logger.info(
            "Agent execution started in the background for "
            "conversation {conversation_id}."
        )
    return {
        "message": f"Message sent to conversation {conversation_id}.",
        "run_started": request.run,
        "state": conversation.state,
    }


@app.post("/conversations/{conversation_id}/run", status_code=202)
async def run_conversation(conversation_id: str, background_tasks: BackgroundTasks):
    """Starts or resumes the agent run for a conversation in the background."""
    conversation = get_conversation(conversation_id)
    await _run_conversation(conversation_id, background_tasks)
    return {
        "message": "Agent execution started in the "
        "background for conversation {conversation_id}.",
        "state": conversation.state,
    }


@app.post("/conversations/{conversation_id}/pause", status_code=202)
def pause_conversation(conversation_id: str):
    conversation = get_conversation(conversation_id)
    conversation.pause()
    logger.info(f"Pause request sent to conversation {conversation_id}")
    return {"message": "Pause request sent."}


@app.post("/conversations/{conversation_id}/respond_to_confirmation", status_code=202)
async def respond_to_confirmation(
    conversation_id: str,
    request: ConfirmationResponseRequest,
    background_tasks: BackgroundTasks,
):
    conversation = get_conversation(conversation_id)
    if not conversation.state.agent_waiting_for_confirmation:
        raise HTTPException(
            status_code=400, detail="Agent is not waiting for confirmation."
        )
    if request.accept:
        logger.info(
            f"User accepted action for conversation {conversation_id}. Resuming run."
        )
        await run_conversation(conversation_id, background_tasks)
        return {"message": "Action accepted. Agent is resuming execution."}
    else:
        logger.info(f"User rejected action for conversation {conversation_id}.")
        conversation.reject_pending_actions(request.reason)
        return {"message": "Action rejected."}


@app.delete("/conversations/{conversation_id}", status_code=204)
def close_conversation(conversation_id: str):
    conversation = get_conversation(conversation_id)
    conversation.close()
    del active_conversations[conversation_id]
    logger.info(f"Successfully closed and removed conversation {conversation_id}.")
    return None


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
