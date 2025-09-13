"""Client for accessing the OpenHands agent-sdk API server."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from openhands.sdk.context import AgentContext
from openhands.sdk.event import Event, EventBase
from openhands.sdk.llm import LLM
from openhands.sdk.logger import get_logger
from openhands.sdk.tool import ToolSpec


logger = get_logger(__name__)

SERVER_URL = os.getenv("OPENHANDS_SERVER_URL", "http://localhost:9000").rstrip("/")
MASTER_KEY = os.getenv("MASTER_KEY", "testkey")


class OpenHandsClient:
    """Tiny convenience client around the OpenHands server API.

    Design goals:
    - Keep it small and dependency-light (httpx + pydantic only)
    - Environment-variable defaults; override via kwargs
    - Clean, typed methods that mirror the API
    - No unnecessary attributes / methods
    """

    def __init__(
        self,
        *,
        server_url: str | None = None,
        master_key: str | None = None,
        litellm_api_key: str | None = None,
        request_timeout: float | None = None,
    ) -> None:
        self.server_url = (
            server_url or os.getenv("OPENHANDS_SERVER_URL") or "http://localhost:9000"
        ).rstrip("/")
        self.master_key = master_key or os.getenv("MASTER_KEY") or ""
        self.request_timeout = request_timeout or float(
            os.getenv("REQUEST_TIMEOUT", 300)
        )

        if not self.master_key:
            raise RuntimeError("MASTER_KEY environment variable is not set.")

        self._client = httpx.Client(
            base_url=self.server_url,
            timeout=self.request_timeout,
            headers={
                "X-Master-Key": self.master_key,
                "Content-Type": "application/json",
            },
        )

    # --- lifecycle ---------------------------------------------------------
    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "OpenHandsClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: D401 (context manager)
        self.close()

    # --- low-level request helper -----------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        json_data: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        try:
            r = self._client.request(method, path, json=json_data, params=params)
            r.raise_for_status()
            return r.json() if r.content else None
        except httpx.HTTPError:
            logger.error(
                "HTTP %s %s failed. content=%s",
                method,
                path,
                (r.content if "r" in locals() else b"<no response>"),  # type: ignore
                exc_info=True,
            )
            raise

    # --- API methods -------------------------------------------------------
    def start_conversation(
        self,
        *,
        llm: LLM,
        tools: list[ToolSpec],
        mcp_config: dict[str, Any] | None = None,
        agent_context: AgentContext | None = None,
        confirmation_mode: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        payload: dict[str, Any] = {
            "llm": llm.model_dump_with_secrets(),
            "tools": [t.model_dump() for t in tools],
            "mcp_config": mcp_config,
            "agent_context": agent_context,
            "confirmation_mode": confirmation_mode,
        }
        res = self._request("POST", "/conversations/", json_data=payload)
        return res["conversation_id"], res["state"]

    def send_message_and_run(self, conversation_id: str, text: str) -> dict[str, Any]:
        payload = {
            "role": "user",
            "content": [{"type": "text", "text": text}],
            "run": True,
        }
        return self._request(
            "POST", f"/conversations/{conversation_id}/messages", json_data=payload
        )["state"]

    def respond_to_confirmation(
        self, conversation_id: str, accept: bool, reason: str = ""
    ) -> None:
        payload = {
            "accept": accept,
            "reason": (reason or ("Accepted" if accept else "Rejected")),
        }
        self._request(
            "POST",
            f"/conversations/{conversation_id}/respond_to_confirmation",
            json_data=payload,
        )

    def get_state(self, conversation_id: str) -> dict[str, Any]:
        return self._request("GET", f"/conversations/{conversation_id}")

    def get_events(
        self, conversation_id: str, *, start: int = 0, limit: int = 1000
    ) -> list[Event]:
        events = self._request(
            "GET",
            f"/conversations/{conversation_id}/events",
            params={"start": start, "limit": limit},
        )
        return [EventBase.model_validate(e) for e in events]

    # --- helpers -----------------------------------------------------------
    def wait_until_idle(
        self,
        conversation_id: str,
        *,
        poll_s: float = 1.0,
        max_wait_s: int = 600,
        auto_confirm: bool = True,
    ) -> dict[str, Any]:
        """Block until the agent run finishes or a timeout occurs."""
        deadline = time.time() + max_wait_s
        while True:
            state = self.get_state(conversation_id)
            if state.get("agent_waiting_for_confirmation") and auto_confirm:
                self.respond_to_confirmation(
                    conversation_id, accept=True, reason="Auto-accept from client"
                )
            elif state.get("agent_finished"):
                return state

            if time.time() > deadline:
                raise TimeoutError("Timed out waiting for agent to finish.")
            time.sleep(poll_s)
