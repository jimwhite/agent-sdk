from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.tool_spec_params import ToolSpecParams


T = TypeVar("T", bound="ToolSpec")


@_attrs_define
class ToolSpec:
    """Defines a tool to be initialized for the agent.

    This is only used in agent-sdk for type schema for server use.

        Attributes:
            name (str): Name of the tool class, e.g., 'BashTool', must be importable from openhands.tools
            params (Union[Unset, ToolSpecParams]): Parameters for the tool's .create() method, e.g., {'working_dir': '/app'}
    """

    name: str
    params: Union[Unset, "ToolSpecParams"] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        params: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.params, Unset):
            params = self.params.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
            }
        )
        if params is not UNSET:
            field_dict["params"] = params

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.tool_spec_params import ToolSpecParams

        d = dict(src_dict)
        name = d.pop("name")

        _params = d.pop("params", UNSET)
        params: Union[Unset, ToolSpecParams]
        if isinstance(_params, Unset):
            params = UNSET
        else:
            params = ToolSpecParams.from_dict(_params)

        tool_spec = cls(
            name=name,
            params=params,
        )

        tool_spec.additional_properties = d
        return tool_spec

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
