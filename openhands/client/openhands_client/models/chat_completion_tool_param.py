from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.chat_completion_cached_content import ChatCompletionCachedContent
    from ..models.chat_completion_tool_param_function_chunk import ChatCompletionToolParamFunctionChunk


T = TypeVar("T", bound="ChatCompletionToolParam")


@_attrs_define
class ChatCompletionToolParam:
    """
    Attributes:
        type_ (Union[Literal['function'], str]):
        function (ChatCompletionToolParamFunctionChunk):
        cache_control (Union[Unset, ChatCompletionCachedContent]):
    """

    type_: Union[Literal["function"], str]
    function: "ChatCompletionToolParamFunctionChunk"
    cache_control: Union[Unset, "ChatCompletionCachedContent"] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_: Union[Literal["function"], str]
        type_ = self.type_

        function = self.function.to_dict()

        cache_control: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.cache_control, Unset):
            cache_control = self.cache_control.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "function": function,
            }
        )
        if cache_control is not UNSET:
            field_dict["cache_control"] = cache_control

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.chat_completion_cached_content import ChatCompletionCachedContent
        from ..models.chat_completion_tool_param_function_chunk import ChatCompletionToolParamFunctionChunk

        d = dict(src_dict)

        def _parse_type_(data: object) -> Union[Literal["function"], str]:
            type_type_0 = cast(Literal["function"], data)
            if type_type_0 != "function":
                raise ValueError(f"type_type_0 must match const 'function', got '{type_type_0}'")
            return type_type_0
            return cast(Union[Literal["function"], str], data)

        type_ = _parse_type_(d.pop("type"))

        function = ChatCompletionToolParamFunctionChunk.from_dict(d.pop("function"))

        _cache_control = d.pop("cache_control", UNSET)
        cache_control: Union[Unset, ChatCompletionCachedContent]
        if isinstance(_cache_control, Unset):
            cache_control = UNSET
        else:
            cache_control = ChatCompletionCachedContent.from_dict(_cache_control)

        chat_completion_tool_param = cls(
            type_=type_,
            function=function,
            cache_control=cache_control,
        )

        chat_completion_tool_param.additional_properties = d
        return chat_completion_tool_param

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
