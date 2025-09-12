from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.agent_context import AgentContext
    from ..models.llm import LLM
    from ..models.start_conversation_request_mcp_config import StartConversationRequestMcpConfig
    from ..models.tool_spec import ToolSpec


T = TypeVar("T", bound="StartConversationRequest")


@_attrs_define
class StartConversationRequest:
    """Payload to create a new conversation.

    Attributes:
        llm (LLM): Refactored LLM: simple `completion()`, centralized Telemetry, tiny helpers.
        tools (Union[Unset, list['ToolSpec']]): List of tools to initialize for the agent.
        mcp_config (Union[Unset, StartConversationRequestMcpConfig]): Optional MCP configuration dictionary to create
            MCP tools.
        agent_context (Union['AgentContext', None, Unset]): Optional AgentContext to initialize the agent with specific
            context.
        working_dir (Union[Unset, str]): Working directory for the agent to work in. Will be created if it doesn't
            exist. Default: '.'.
        confirmation_mode (Union[Unset, bool]): If true, the agent will enter confirmation mode, requiring user approval
            for actions. Default: False.
    """

    llm: "LLM"
    tools: Union[Unset, list["ToolSpec"]] = UNSET
    mcp_config: Union[Unset, "StartConversationRequestMcpConfig"] = UNSET
    agent_context: Union["AgentContext", None, Unset] = UNSET
    working_dir: Union[Unset, str] = "."
    confirmation_mode: Union[Unset, bool] = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.agent_context import AgentContext

        llm = self.llm.to_dict()

        tools: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.tools, Unset):
            tools = []
            for tools_item_data in self.tools:
                tools_item = tools_item_data.to_dict()
                tools.append(tools_item)

        mcp_config: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.mcp_config, Unset):
            mcp_config = self.mcp_config.to_dict()

        agent_context: Union[None, Unset, dict[str, Any]]
        if isinstance(self.agent_context, Unset):
            agent_context = UNSET
        elif isinstance(self.agent_context, AgentContext):
            agent_context = self.agent_context.to_dict()
        else:
            agent_context = self.agent_context

        working_dir = self.working_dir

        confirmation_mode = self.confirmation_mode

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "llm": llm,
            }
        )
        if tools is not UNSET:
            field_dict["tools"] = tools
        if mcp_config is not UNSET:
            field_dict["mcp_config"] = mcp_config
        if agent_context is not UNSET:
            field_dict["agent_context"] = agent_context
        if working_dir is not UNSET:
            field_dict["working_dir"] = working_dir
        if confirmation_mode is not UNSET:
            field_dict["confirmation_mode"] = confirmation_mode

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.agent_context import AgentContext
        from ..models.llm import LLM
        from ..models.start_conversation_request_mcp_config import StartConversationRequestMcpConfig
        from ..models.tool_spec import ToolSpec

        d = dict(src_dict)
        llm = LLM.from_dict(d.pop("llm"))

        tools = []
        _tools = d.pop("tools", UNSET)
        for tools_item_data in _tools or []:
            tools_item = ToolSpec.from_dict(tools_item_data)

            tools.append(tools_item)

        _mcp_config = d.pop("mcp_config", UNSET)
        mcp_config: Union[Unset, StartConversationRequestMcpConfig]
        if isinstance(_mcp_config, Unset):
            mcp_config = UNSET
        else:
            mcp_config = StartConversationRequestMcpConfig.from_dict(_mcp_config)

        def _parse_agent_context(data: object) -> Union["AgentContext", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                agent_context_type_0 = AgentContext.from_dict(data)

                return agent_context_type_0
            except:  # noqa: E722
                pass
            return cast(Union["AgentContext", None, Unset], data)

        agent_context = _parse_agent_context(d.pop("agent_context", UNSET))

        working_dir = d.pop("working_dir", UNSET)

        confirmation_mode = d.pop("confirmation_mode", UNSET)

        start_conversation_request = cls(
            llm=llm,
            tools=tools,
            mcp_config=mcp_config,
            agent_context=agent_context,
            working_dir=working_dir,
            confirmation_mode=confirmation_mode,
        )

        start_conversation_request.additional_properties = d
        return start_conversation_request

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
