from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.finish_action_security_risk import FinishActionSecurityRisk, check_finish_action_security_risk
from ..types import UNSET, Unset

T = TypeVar("T", bound="FinishAction")


@_attrs_define
class FinishAction:
    """
    Attributes:
        message (str): Final message to send to the user.
        kind (str): Property to create kind field from class name when serializing.
        security_risk (Union[Unset, FinishActionSecurityRisk]): The LLM's assessment of the safety risk of this action.
            Default: 'UNKNOWN'.
    """

    message: str
    kind: str
    security_risk: Union[Unset, FinishActionSecurityRisk] = "UNKNOWN"

    def to_dict(self) -> dict[str, Any]:
        message = self.message

        kind = self.kind

        security_risk: Union[Unset, str] = UNSET
        if not isinstance(self.security_risk, Unset):
            security_risk = self.security_risk

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "message": message,
                "kind": kind,
            }
        )
        if security_risk is not UNSET:
            field_dict["security_risk"] = security_risk

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        message = d.pop("message")

        kind = d.pop("kind")

        _security_risk = d.pop("security_risk", UNSET)
        security_risk: Union[Unset, FinishActionSecurityRisk]
        if isinstance(_security_risk, Unset):
            security_risk = UNSET
        else:
            security_risk = check_finish_action_security_risk(_security_risk)

        finish_action = cls(
            message=message,
            kind=kind,
            security_risk=security_risk,
        )

        return finish_action
