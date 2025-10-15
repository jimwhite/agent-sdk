from importlib.metadata import PackageNotFoundError, version

from openhands_sdk.agent import Agent, AgentBase
from openhands_sdk.context import AgentContext
from openhands_sdk.context.condenser import (
    LLMSummarizingCondenser,
)
from openhands_sdk.conversation import (
    BaseConversation,
    Conversation,
    ConversationCallbackType,
    LocalConversation,
    RemoteConversation,
)
from openhands_sdk.conversation.conversation_stats import ConversationStats
from openhands_sdk.event import Event, LLMConvertibleEvent
from openhands_sdk.event.llm_convertible import MessageEvent
from openhands_sdk.io import FileStore, LocalFileStore
from openhands_sdk.llm import (
    LLM,
    ImageContent,
    LLMRegistry,
    Message,
    RedactedThinkingBlock,
    RegistryEvent,
    TextContent,
    ThinkingBlock,
)
from openhands_sdk.logger import get_logger
from openhands_sdk.mcp import (
    MCPClient,
    MCPToolDefinition,
    MCPToolObservation,
    create_mcp_tools,
)
from openhands_sdk.tool import (
    Action,
    Observation,
    Tool,
    ToolBase,
    ToolDefinition,
    list_registered_tools,
    register_tool,
    resolve_tool,
)
from openhands_sdk.workspace import (
    LocalWorkspace,
    RemoteWorkspace,
    Workspace,
)


try:
    __version__ = version("openhands-sdk")
except PackageNotFoundError:
    __version__ = "0.0.0"  # fallback for editable/unbuilt environments

__all__ = [
    "LLM",
    "LLMRegistry",
    "ConversationStats",
    "RegistryEvent",
    "Message",
    "TextContent",
    "ImageContent",
    "ThinkingBlock",
    "RedactedThinkingBlock",
    "Tool",
    "ToolDefinition",
    "ToolBase",
    "AgentBase",
    "Agent",
    "Action",
    "Observation",
    "MCPClient",
    "MCPToolDefinition",
    "MCPToolObservation",
    "MessageEvent",
    "create_mcp_tools",
    "get_logger",
    "Conversation",
    "BaseConversation",
    "LocalConversation",
    "RemoteConversation",
    "ConversationCallbackType",
    "Event",
    "LLMConvertibleEvent",
    "AgentContext",
    "LLMSummarizingCondenser",
    "FileStore",
    "LocalFileStore",
    "register_tool",
    "resolve_tool",
    "list_registered_tools",
    "Workspace",
    "LocalWorkspace",
    "RemoteWorkspace",
    "__version__",
]
