from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.token_usage import TokenUsage


T = TypeVar("T", bound="MetricsSnapshot")


@_attrs_define
class MetricsSnapshot:
    """A snapshot of metrics at a point in time.

    Does not include lists of individual costs, latencies, or token usages.

        Attributes:
            model_name (Union[Unset, str]): Name of the model Default: 'default'.
            accumulated_cost (Union[Unset, float]): Total accumulated cost, must be non-negative Default: 0.0.
            max_budget_per_task (Union[None, Unset, float]): Maximum budget per task
            accumulated_token_usage (Union['TokenUsage', None, Unset]): Accumulated token usage across all calls
    """

    model_name: Union[Unset, str] = "default"
    accumulated_cost: Union[Unset, float] = 0.0
    max_budget_per_task: Union[None, Unset, float] = UNSET
    accumulated_token_usage: Union["TokenUsage", None, Unset] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.token_usage import TokenUsage

        model_name = self.model_name

        accumulated_cost = self.accumulated_cost

        max_budget_per_task: Union[None, Unset, float]
        if isinstance(self.max_budget_per_task, Unset):
            max_budget_per_task = UNSET
        else:
            max_budget_per_task = self.max_budget_per_task

        accumulated_token_usage: Union[None, Unset, dict[str, Any]]
        if isinstance(self.accumulated_token_usage, Unset):
            accumulated_token_usage = UNSET
        elif isinstance(self.accumulated_token_usage, TokenUsage):
            accumulated_token_usage = self.accumulated_token_usage.to_dict()
        else:
            accumulated_token_usage = self.accumulated_token_usage

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if model_name is not UNSET:
            field_dict["model_name"] = model_name
        if accumulated_cost is not UNSET:
            field_dict["accumulated_cost"] = accumulated_cost
        if max_budget_per_task is not UNSET:
            field_dict["max_budget_per_task"] = max_budget_per_task
        if accumulated_token_usage is not UNSET:
            field_dict["accumulated_token_usage"] = accumulated_token_usage

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.token_usage import TokenUsage

        d = dict(src_dict)
        model_name = d.pop("model_name", UNSET)

        accumulated_cost = d.pop("accumulated_cost", UNSET)

        def _parse_max_budget_per_task(data: object) -> Union[None, Unset, float]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, float], data)

        max_budget_per_task = _parse_max_budget_per_task(d.pop("max_budget_per_task", UNSET))

        def _parse_accumulated_token_usage(data: object) -> Union["TokenUsage", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                accumulated_token_usage_type_0 = TokenUsage.from_dict(data)

                return accumulated_token_usage_type_0
            except:  # noqa: E722
                pass
            return cast(Union["TokenUsage", None, Unset], data)

        accumulated_token_usage = _parse_accumulated_token_usage(d.pop("accumulated_token_usage", UNSET))

        metrics_snapshot = cls(
            model_name=model_name,
            accumulated_cost=accumulated_cost,
            max_budget_per_task=max_budget_per_task,
            accumulated_token_usage=accumulated_token_usage,
        )

        metrics_snapshot.additional_properties = d
        return metrics_snapshot

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
