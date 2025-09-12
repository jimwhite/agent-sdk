from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ConfirmationResponseRequest")


@_attrs_define
class ConfirmationResponseRequest:
    """Payload to accept or reject a pending action.

    Attributes:
        accept (bool):
        reason (Union[Unset, str]):  Default: 'User rejected the action.'.
    """

    accept: bool
    reason: Union[Unset, str] = "User rejected the action."
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        accept = self.accept

        reason = self.reason

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "accept": accept,
            }
        )
        if reason is not UNSET:
            field_dict["reason"] = reason

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        accept = d.pop("accept")

        reason = d.pop("reason", UNSET)

        confirmation_response_request = cls(
            accept=accept,
            reason=reason,
        )

        confirmation_response_request.additional_properties = d
        return confirmation_response_request

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
