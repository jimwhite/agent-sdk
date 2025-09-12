from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.message_role import MessageRole, check_message_role
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.chat_completion_message_tool_call import ChatCompletionMessageToolCall
    from ..models.image_content import ImageContent
    from ..models.text_content import TextContent


T = TypeVar("T", bound="Message")


@_attrs_define
class Message:
    """
    Attributes:
        role (MessageRole):
        content (Union[Unset, list[Union['ImageContent', 'TextContent']]]):
        cache_enabled (Union[Unset, bool]):  Default: False.
        vision_enabled (Union[Unset, bool]):  Default: False.
        function_calling_enabled (Union[Unset, bool]):  Default: False.
        tool_calls (Union[None, Unset, list['ChatCompletionMessageToolCall']]):
        tool_call_id (Union[None, Unset, str]):
        name (Union[None, Unset, str]):
        force_string_serializer (Union[Unset, bool]):  Default: False.
        reasoning_content (Union[None, Unset, str]): Intermediate reasoning/thinking content from reasoning models
    """

    role: MessageRole
    content: Union[Unset, list[Union["ImageContent", "TextContent"]]] = UNSET
    cache_enabled: Union[Unset, bool] = False
    vision_enabled: Union[Unset, bool] = False
    function_calling_enabled: Union[Unset, bool] = False
    tool_calls: Union[None, Unset, list["ChatCompletionMessageToolCall"]] = UNSET
    tool_call_id: Union[None, Unset, str] = UNSET
    name: Union[None, Unset, str] = UNSET
    force_string_serializer: Union[Unset, bool] = False
    reasoning_content: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.text_content import TextContent

        role: str = self.role

        content: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.content, Unset):
            content = []
            for content_item_data in self.content:
                content_item: dict[str, Any]
                if isinstance(content_item_data, TextContent):
                    content_item = content_item_data.to_dict()
                else:
                    content_item = content_item_data.to_dict()

                content.append(content_item)

        cache_enabled = self.cache_enabled

        vision_enabled = self.vision_enabled

        function_calling_enabled = self.function_calling_enabled

        tool_calls: Union[None, Unset, list[dict[str, Any]]]
        if isinstance(self.tool_calls, Unset):
            tool_calls = UNSET
        elif isinstance(self.tool_calls, list):
            tool_calls = []
            for tool_calls_type_0_item_data in self.tool_calls:
                tool_calls_type_0_item = tool_calls_type_0_item_data.to_dict()
                tool_calls.append(tool_calls_type_0_item)

        else:
            tool_calls = self.tool_calls

        tool_call_id: Union[None, Unset, str]
        if isinstance(self.tool_call_id, Unset):
            tool_call_id = UNSET
        else:
            tool_call_id = self.tool_call_id

        name: Union[None, Unset, str]
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        force_string_serializer = self.force_string_serializer

        reasoning_content: Union[None, Unset, str]
        if isinstance(self.reasoning_content, Unset):
            reasoning_content = UNSET
        else:
            reasoning_content = self.reasoning_content

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "role": role,
            }
        )
        if content is not UNSET:
            field_dict["content"] = content
        if cache_enabled is not UNSET:
            field_dict["cache_enabled"] = cache_enabled
        if vision_enabled is not UNSET:
            field_dict["vision_enabled"] = vision_enabled
        if function_calling_enabled is not UNSET:
            field_dict["function_calling_enabled"] = function_calling_enabled
        if tool_calls is not UNSET:
            field_dict["tool_calls"] = tool_calls
        if tool_call_id is not UNSET:
            field_dict["tool_call_id"] = tool_call_id
        if name is not UNSET:
            field_dict["name"] = name
        if force_string_serializer is not UNSET:
            field_dict["force_string_serializer"] = force_string_serializer
        if reasoning_content is not UNSET:
            field_dict["reasoning_content"] = reasoning_content

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.chat_completion_message_tool_call import ChatCompletionMessageToolCall
        from ..models.image_content import ImageContent
        from ..models.text_content import TextContent

        d = dict(src_dict)
        role = check_message_role(d.pop("role"))

        content = []
        _content = d.pop("content", UNSET)
        for content_item_data in _content or []:

            def _parse_content_item(data: object) -> Union["ImageContent", "TextContent"]:
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    content_item_type_0 = TextContent.from_dict(data)

                    return content_item_type_0
                except:  # noqa: E722
                    pass
                if not isinstance(data, dict):
                    raise TypeError()
                content_item_type_1 = ImageContent.from_dict(data)

                return content_item_type_1

            content_item = _parse_content_item(content_item_data)

            content.append(content_item)

        cache_enabled = d.pop("cache_enabled", UNSET)

        vision_enabled = d.pop("vision_enabled", UNSET)

        function_calling_enabled = d.pop("function_calling_enabled", UNSET)

        def _parse_tool_calls(data: object) -> Union[None, Unset, list["ChatCompletionMessageToolCall"]]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                tool_calls_type_0 = []
                _tool_calls_type_0 = data
                for tool_calls_type_0_item_data in _tool_calls_type_0:
                    tool_calls_type_0_item = ChatCompletionMessageToolCall.from_dict(tool_calls_type_0_item_data)

                    tool_calls_type_0.append(tool_calls_type_0_item)

                return tool_calls_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, list["ChatCompletionMessageToolCall"]], data)

        tool_calls = _parse_tool_calls(d.pop("tool_calls", UNSET))

        def _parse_tool_call_id(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        tool_call_id = _parse_tool_call_id(d.pop("tool_call_id", UNSET))

        def _parse_name(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        name = _parse_name(d.pop("name", UNSET))

        force_string_serializer = d.pop("force_string_serializer", UNSET)

        def _parse_reasoning_content(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        reasoning_content = _parse_reasoning_content(d.pop("reasoning_content", UNSET))

        message = cls(
            role=role,
            content=content,
            cache_enabled=cache_enabled,
            vision_enabled=vision_enabled,
            function_calling_enabled=function_calling_enabled,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            name=name,
            force_string_serializer=force_string_serializer,
            reasoning_content=reasoning_content,
        )

        message.additional_properties = d
        return message

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
