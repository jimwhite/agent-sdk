from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.agent_base_tools_type_0 import AgentBaseToolsType0
    from ..models.agent_context import AgentContext
    from ..models.llm import LLM
    from ..models.tool import Tool


T = TypeVar("T", bound="AgentBase")


@_attrs_define
class AgentBase:
    """
    Attributes:
        llm (LLM): Refactored LLM: simple `completion()`, centralized Telemetry, tiny helpers.
        kind (str): Property to create kind field from class name when serializing.
        agent_context (Union['AgentContext', None, Unset]):
        tools (Union['AgentBaseToolsType0', Unset, list['Tool']]): Mapping of tool name to Tool instance that the agent
            can use. If a list is provided, it should be converted to a mapping by tool name. We need to define this as
            ToolType for discriminated union.
    """

    llm: "LLM"
    kind: str
    agent_context: Union["AgentContext", None, Unset] = UNSET
    tools: Union["AgentBaseToolsType0", Unset, list["Tool"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.agent_base_tools_type_0 import AgentBaseToolsType0
        from ..models.agent_context import AgentContext

        llm = self.llm.to_dict()

        kind = self.kind

        agent_context: Union[None, Unset, dict[str, Any]]
        if isinstance(self.agent_context, Unset):
            agent_context = UNSET
        elif isinstance(self.agent_context, AgentContext):
            agent_context = self.agent_context.to_dict()
        else:
            agent_context = self.agent_context

        tools: Union[Unset, dict[str, Any], list[dict[str, Any]]]
        if isinstance(self.tools, Unset):
            tools = UNSET
        elif isinstance(self.tools, AgentBaseToolsType0):
            tools = self.tools.to_dict()
        else:
            tools = []
            for tools_type_1_item_data in self.tools:
                tools_type_1_item = tools_type_1_item_data.to_dict()
                tools.append(tools_type_1_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "llm": llm,
                "kind": kind,
            }
        )
        if agent_context is not UNSET:
            field_dict["agent_context"] = agent_context
        if tools is not UNSET:
            field_dict["tools"] = tools

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.agent_base_tools_type_0 import AgentBaseToolsType0
        from ..models.agent_context import AgentContext
        from ..models.llm import LLM
        from ..models.tool import Tool

        d = dict(src_dict)
        llm = LLM.from_dict(d.pop("llm"))

        kind = d.pop("kind")

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

        def _parse_tools(data: object) -> Union["AgentBaseToolsType0", Unset, list["Tool"]]:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                tools_type_0 = AgentBaseToolsType0.from_dict(data)

                return tools_type_0
            except:  # noqa: E722
                pass
            if not isinstance(data, list):
                raise TypeError()
            tools_type_1 = []
            _tools_type_1 = data
            for tools_type_1_item_data in _tools_type_1:
                tools_type_1_item = Tool.from_dict(tools_type_1_item_data)

                tools_type_1.append(tools_type_1_item)

            return tools_type_1

        tools = _parse_tools(d.pop("tools", UNSET))

        agent_base = cls(
            llm=llm,
            kind=kind,
            agent_context=agent_context,
            tools=tools,
        )

        agent_base.additional_properties = d
        return agent_base

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
