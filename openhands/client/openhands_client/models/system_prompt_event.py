from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.system_prompt_event_source import SystemPromptEventSource, check_system_prompt_event_source
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.chat_completion_tool_param import ChatCompletionToolParam
    from ..models.text_content import TextContent


T = TypeVar("T", bound="SystemPromptEvent")


@_attrs_define
class SystemPromptEvent:
    """System prompt added by the agent.

    Attributes:
        system_prompt (TextContent):
        tools (list['ChatCompletionToolParam']): List of tools in OpenAI tool format
        kind (str): Property to create kind field from class name when serializing.
        id (Union[Unset, str]): Unique event id (ULID/UUID)
        timestamp (Union[Unset, str]): Event timestamp
        source (Union[Unset, SystemPromptEventSource]):  Default: 'agent'.
    """

    system_prompt: "TextContent"
    tools: list["ChatCompletionToolParam"]
    kind: str
    id: Union[Unset, str] = UNSET
    timestamp: Union[Unset, str] = UNSET
    source: Union[Unset, SystemPromptEventSource] = "agent"

    def to_dict(self) -> dict[str, Any]:
        system_prompt = self.system_prompt.to_dict()

        tools = []
        for tools_item_data in self.tools:
            tools_item = tools_item_data.to_dict()
            tools.append(tools_item)

        kind = self.kind

        id = self.id

        timestamp = self.timestamp

        source: Union[Unset, str] = UNSET
        if not isinstance(self.source, Unset):
            source = self.source

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "system_prompt": system_prompt,
                "tools": tools,
                "kind": kind,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if timestamp is not UNSET:
            field_dict["timestamp"] = timestamp
        if source is not UNSET:
            field_dict["source"] = source

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.chat_completion_tool_param import ChatCompletionToolParam
        from ..models.text_content import TextContent

        d = dict(src_dict)
        system_prompt = TextContent.from_dict(d.pop("system_prompt"))

        tools = []
        _tools = d.pop("tools")
        for tools_item_data in _tools:
            tools_item = ChatCompletionToolParam.from_dict(tools_item_data)

            tools.append(tools_item)

        kind = d.pop("kind")

        id = d.pop("id", UNSET)

        timestamp = d.pop("timestamp", UNSET)

        _source = d.pop("source", UNSET)
        source: Union[Unset, SystemPromptEventSource]
        if isinstance(_source, Unset):
            source = UNSET
        else:
            source = check_system_prompt_event_source(_source)

        system_prompt_event = cls(
            system_prompt=system_prompt,
            tools=tools,
            kind=kind,
            id=id,
            timestamp=timestamp,
            source=source,
        )

        return system_prompt_event
