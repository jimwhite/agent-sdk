from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="TokenUsage")


@_attrs_define
class TokenUsage:
    """Metric tracking detailed token usage per completion call.

    Attributes:
        model (Union[Unset, str]):  Default: ''.
        prompt_tokens (Union[Unset, int]): Prompt tokens must be non-negative Default: 0.
        completion_tokens (Union[Unset, int]): Completion tokens must be non-negative Default: 0.
        cache_read_tokens (Union[Unset, int]): Cache read tokens must be non-negative Default: 0.
        cache_write_tokens (Union[Unset, int]): Cache write tokens must be non-negative Default: 0.
        reasoning_tokens (Union[Unset, int]): Reasoning tokens must be non-negative Default: 0.
        context_window (Union[Unset, int]): Context window must be non-negative Default: 0.
        per_turn_token (Union[Unset, int]): Per turn tokens must be non-negative Default: 0.
        response_id (Union[Unset, str]):  Default: ''.
    """

    model: Union[Unset, str] = ""
    prompt_tokens: Union[Unset, int] = 0
    completion_tokens: Union[Unset, int] = 0
    cache_read_tokens: Union[Unset, int] = 0
    cache_write_tokens: Union[Unset, int] = 0
    reasoning_tokens: Union[Unset, int] = 0
    context_window: Union[Unset, int] = 0
    per_turn_token: Union[Unset, int] = 0
    response_id: Union[Unset, str] = ""
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        model = self.model

        prompt_tokens = self.prompt_tokens

        completion_tokens = self.completion_tokens

        cache_read_tokens = self.cache_read_tokens

        cache_write_tokens = self.cache_write_tokens

        reasoning_tokens = self.reasoning_tokens

        context_window = self.context_window

        per_turn_token = self.per_turn_token

        response_id = self.response_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if model is not UNSET:
            field_dict["model"] = model
        if prompt_tokens is not UNSET:
            field_dict["prompt_tokens"] = prompt_tokens
        if completion_tokens is not UNSET:
            field_dict["completion_tokens"] = completion_tokens
        if cache_read_tokens is not UNSET:
            field_dict["cache_read_tokens"] = cache_read_tokens
        if cache_write_tokens is not UNSET:
            field_dict["cache_write_tokens"] = cache_write_tokens
        if reasoning_tokens is not UNSET:
            field_dict["reasoning_tokens"] = reasoning_tokens
        if context_window is not UNSET:
            field_dict["context_window"] = context_window
        if per_turn_token is not UNSET:
            field_dict["per_turn_token"] = per_turn_token
        if response_id is not UNSET:
            field_dict["response_id"] = response_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        model = d.pop("model", UNSET)

        prompt_tokens = d.pop("prompt_tokens", UNSET)

        completion_tokens = d.pop("completion_tokens", UNSET)

        cache_read_tokens = d.pop("cache_read_tokens", UNSET)

        cache_write_tokens = d.pop("cache_write_tokens", UNSET)

        reasoning_tokens = d.pop("reasoning_tokens", UNSET)

        context_window = d.pop("context_window", UNSET)

        per_turn_token = d.pop("per_turn_token", UNSET)

        response_id = d.pop("response_id", UNSET)

        token_usage = cls(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
            reasoning_tokens=reasoning_tokens,
            context_window=context_window,
            per_turn_token=per_turn_token,
            response_id=response_id,
        )

        token_usage.additional_properties = d
        return token_usage

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
