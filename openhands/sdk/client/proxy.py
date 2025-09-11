"""Simplified proxy implementation using automatic translator."""

from typing import Any, Dict, List, Optional, Type, TypeVar, cast

import httpx
from pydantic import BaseModel

from openhands.sdk.agent import Agent
from openhands.sdk.conversation import Conversation
from openhands.sdk.llm import LLM, Message
from openhands.sdk.logger import get_logger


logger = get_logger(__name__)

T = TypeVar("T")


class ProxyError(Exception):
    """Base exception for proxy-related errors."""

    pass


class GenericProxy:
    """Generic proxy that can handle any BaseModel automatically."""

    def __init__(self, proxy_client: "Proxy", original_class: Type, **kwargs):
        self._proxy = proxy_client
        self._original_class = original_class
        self._data = kwargs
        self._class_name = original_class.__name__

    def model_dump(self) -> Dict[str, Any]:
        """Return the object data as a dictionary."""
        return self._data

    def __getattr__(self, name):
        """Automatically proxy method calls and attribute access."""
        # First check if it's in our stored data
        if name in self._data:
            return self._data[name]

        # Check if the original class has this attribute/method
        if hasattr(self._original_class, name):
            original_attr = getattr(self._original_class, name)

            # If it's a method, create a proxy method
            if callable(original_attr):

                def proxy_method(*args, **kwargs):
                    # Serialize arguments
                    serialized_args = []
                    for arg in args:
                        if hasattr(arg, "model_dump"):
                            serialized_args.append(arg.model_dump())
                        else:
                            serialized_args.append(arg)

                    serialized_kwargs = {}
                    for k, v in kwargs.items():
                        if hasattr(v, "model_dump"):
                            serialized_kwargs[k] = v.model_dump()
                        else:
                            serialized_kwargs[k] = v

                    # Make remote call
                    data = {
                        "class_name": self._class_name,
                        "method_name": name,
                        "instance_data": self._data,
                        "args": serialized_args,
                        "kwargs": serialized_kwargs,
                    }

                    response = self._proxy._make_request("POST", "/proxy/call", data)

                    # Handle response - if it's a BaseModel, deserialize it
                    result = response.get("result")
                    if isinstance(result, dict) and "model_type" in result:
                        # This is a serialized BaseModel, deserialize it
                        model_class = globals().get(result["model_type"])
                        if model_class and issubclass(model_class, BaseModel):
                            return model_class.model_validate(result["data"])

                    return result

                return proxy_method
            else:
                # It's a property or attribute
                return original_attr

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )


class ConversationProxy:
    """Special proxy for Conversation that uses the existing conversation API."""

    def __init__(self, proxy_client: "Proxy"):
        self._proxy = proxy_client
        self._conversation_id: Optional[str] = None

    def send_message(
        self,
        message: Message,
        agent: Optional[Agent] = None,
        tools: Optional[List[Any]] = None,
    ) -> Message:
        """Send a message and get response."""
        data = {
            "message": message.model_dump(),
            "agent": agent.model_dump() if agent else None,
            "tools": [
                tool.model_dump() if hasattr(tool, "model_dump") else str(tool)
                for tool in (tools or [])
            ],
        }
        if self._conversation_id:
            data["conversation_id"] = self._conversation_id

        response = self._proxy._make_request("POST", "/conversation/send_message", data)

        # Store conversation ID for future requests
        if "conversation_id" in response:
            self._conversation_id = response["conversation_id"]

        return Message.model_validate(response["message"])

    def run_conversation(
        self,
        message: Message,
        agent: Agent,
        tools: Optional[List[Any]] = None,
        max_iterations: int = 10,
    ) -> List[Message]:
        """Run a complete conversation."""
        data = {
            "message": message.model_dump(),
            "agent": agent.model_dump(),
            "tools": [
                tool.model_dump() if hasattr(tool, "model_dump") else str(tool)
                for tool in (tools or [])
            ],
            "max_iterations": max_iterations,
        }
        if self._conversation_id:
            data["conversation_id"] = self._conversation_id

        response = self._proxy._make_request(
            "POST", "/conversation/run_conversation", data
        )

        # Store conversation ID for future requests
        if "conversation_id" in response:
            self._conversation_id = response["conversation_id"]

        return [Message.model_validate(msg) for msg in response["messages"]]

    def get_state(self) -> Dict[str, Any]:
        """Get the current conversation state."""
        if not self._conversation_id:
            return {}

        response = self._proxy._make_request(
            "GET", f"/conversation/{self._conversation_id}/state"
        )
        return response

    @property
    def conversation_id(self) -> Optional[str]:
        """Get the conversation ID."""
        return self._conversation_id

    @property
    def messages(self) -> List[Message]:
        """Get all messages in the conversation."""
        state = self.get_state()
        return [Message.model_validate(msg) for msg in state.get("messages", [])]

    @property
    def agent(self) -> Optional[Agent]:
        """Get the current agent."""
        state = self.get_state()
        agent_data = state.get("agent")
        return Agent.model_validate(agent_data) if agent_data else None

    @property
    def llm(self) -> Optional[LLM]:
        """Get the current LLM."""
        state = self.get_state()
        llm_data = state.get("llm")
        return LLM.model_validate(llm_data) if llm_data else None

    @property
    def tools(self) -> List[Any]:
        """Get the current tools."""
        state = self.get_state()
        return state.get("tools", [])

    @property
    def max_iterations(self) -> int:
        """Get the max iterations setting."""
        state = self.get_state()
        return state.get("max_iterations", 10)

    @property
    def iteration_count(self) -> int:
        """Get the current iteration count."""
        state = self.get_state()
        return state.get("iteration_count", 0)

    @property
    def is_complete(self) -> bool:
        """Check if the conversation is complete."""
        state = self.get_state()
        return state.get("is_complete", False)

    @property
    def activated_knowledge_microagents(self) -> List[str]:
        """Get activated knowledge microagents."""
        state = self.get_state()
        return state.get("activated_knowledge_microagents", [])


class Proxy:
    """Main proxy client that handles communication with remote OpenHands server."""

    def __init__(self, url: str, api_key: Optional[str] = None, timeout: float = 30.0):
        """Initialize proxy client.

        Args:
            url: Base URL of the OpenHands server
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=timeout,
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.client.close()

    def _make_request(
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Any:
        """Make HTTP request to the server."""
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                response = self.client.get(url)
            elif method == "POST":
                response = self.client.post(url, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except httpx.RequestError as e:
            raise ProxyError(f"Request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise ProxyError(f"HTTP error {e.response.status_code}: {e.response.text}")

    def health_check(self) -> Dict[str, Any]:
        """Check if the server is alive."""
        return self._make_request("GET", "/alive")

    def import_class(self, cls: Type[T]) -> Type[T]:
        """Import a class and return its proxy version."""
        if cls == Conversation:
            return cast(Type[T], self._create_conversation_class())
        else:
            # Generic proxy for all other classes (Agent, LLM, etc.)
            return cast(Type[T], self._create_generic_class(cls))

    def import_(self, cls: Type[T]) -> Type[T]:
        """Alias for import_class to match the proposed API."""
        return self.import_class(cls)

    def _create_conversation_class(self):
        """Create a Conversation proxy class."""
        proxy_client = self

        class ConversationProxyClass:
            def __init__(self):
                self._proxy_instance = ConversationProxy(proxy_client)

            def __getattr__(self, name):
                # Delegate all attribute access to the proxy instance
                return getattr(self._proxy_instance, name)

        return ConversationProxyClass

    def _create_generic_class(self, original_class: Type):
        """Create a generic proxy class for any BaseModel."""
        proxy_client = self

        class GenericProxyClass:
            def __init__(self, **kwargs):
                self._proxy_instance = GenericProxy(
                    proxy_client, original_class, **kwargs
                )

            def __getattr__(self, name):
                return getattr(self._proxy_instance, name)

        return GenericProxyClass
