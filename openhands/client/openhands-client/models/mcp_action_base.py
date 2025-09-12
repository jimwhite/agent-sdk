from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.mcp_action_base_security_risk import MCPActionBaseSecurityRisk, check_mcp_action_base_security_risk
from ..types import UNSET, Unset

T = TypeVar("T", bound="MCPActionBase")


@_attrs_define
class MCPActionBase:
    """Base schema for MCP input action.

    Attributes:
        kind (str): Property to create kind field from class name when serializing.
        security_risk (Union[Unset, MCPActionBaseSecurityRisk]): The LLM's assessment of the safety risk of this action.
            Default: 'UNKNOWN'.
    """

    kind: str
    security_risk: Union[Unset, MCPActionBaseSecurityRisk] = "UNKNOWN"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        kind = self.kind

        security_risk: Union[Unset, str] = UNSET
        if not isinstance(self.security_risk, Unset):
            security_risk = self.security_risk

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "kind": kind,
            }
        )
        if security_risk is not UNSET:
            field_dict["security_risk"] = security_risk

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        kind = d.pop("kind")

        _security_risk = d.pop("security_risk", UNSET)
        security_risk: Union[Unset, MCPActionBaseSecurityRisk]
        if isinstance(_security_risk, Unset):
            security_risk = UNSET
        else:
            security_risk = check_mcp_action_base_security_risk(_security_risk)

        mcp_action_base = cls(
            kind=kind,
            security_risk=security_risk,
        )

        mcp_action_base.additional_properties = d
        return mcp_action_base

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
