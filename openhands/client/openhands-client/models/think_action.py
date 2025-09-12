from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.think_action_security_risk import ThinkActionSecurityRisk, check_think_action_security_risk
from ..types import UNSET, Unset

T = TypeVar("T", bound="ThinkAction")


@_attrs_define
class ThinkAction:
    """Action for logging a thought without making any changes.

    Attributes:
        thought (str): The thought to log.
        kind (str): Property to create kind field from class name when serializing.
        security_risk (Union[Unset, ThinkActionSecurityRisk]): The LLM's assessment of the safety risk of this action.
            Default: 'UNKNOWN'.
    """

    thought: str
    kind: str
    security_risk: Union[Unset, ThinkActionSecurityRisk] = "UNKNOWN"

    def to_dict(self) -> dict[str, Any]:
        thought = self.thought

        kind = self.kind

        security_risk: Union[Unset, str] = UNSET
        if not isinstance(self.security_risk, Unset):
            security_risk = self.security_risk

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "thought": thought,
                "kind": kind,
            }
        )
        if security_risk is not UNSET:
            field_dict["security_risk"] = security_risk

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        thought = d.pop("thought")

        kind = d.pop("kind")

        _security_risk = d.pop("security_risk", UNSET)
        security_risk: Union[Unset, ThinkActionSecurityRisk]
        if isinstance(_security_risk, Unset):
            security_risk = UNSET
        else:
            security_risk = check_think_action_security_risk(_security_risk)

        think_action = cls(
            thought=thought,
            kind=kind,
            security_risk=security_risk,
        )

        return think_action
