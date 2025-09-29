from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import field_validator

from openhands.sdk.security.risk import SecurityRisk
from openhands.sdk.utils.models import DiscriminatedUnionMixin


if TYPE_CHECKING:
    from openhands.sdk.event.llm_convertible import ActionEvent


class ConfirmationPolicyBase(DiscriminatedUnionMixin, ABC):
    @abstractmethod
    def should_confirm(
        self,
        risk: SecurityRisk = SecurityRisk.UNKNOWN,
        action: "ActionEvent | None" = None,
    ) -> bool:
        """Determine if an action with the given risk level requires confirmation."""
        pass


class AlwaysConfirm(ConfirmationPolicyBase):
    def should_confirm(
        self,
        risk: SecurityRisk = SecurityRisk.UNKNOWN,
        action: "ActionEvent | None" = None,
    ) -> bool:
        # Special case: FinishAction always skips confirmation to preserve existing behavior  # noqa: E501
        if action is not None:
            from openhands.sdk.tool.builtins.finish import FinishAction

            # Check if the action is wrapped in an ActionEvent
            actual_action = getattr(action, "action", action)
            if isinstance(actual_action, FinishAction):
                return False
        return True


class NeverConfirm(ConfirmationPolicyBase):
    def should_confirm(
        self,
        risk: SecurityRisk = SecurityRisk.UNKNOWN,
        action: "ActionEvent | None" = None,
    ) -> bool:
        return False


class ConfirmRisky(ConfirmationPolicyBase):
    threshold: SecurityRisk = SecurityRisk.HIGH
    confirm_unknown: bool = True

    @field_validator("threshold")
    def validate_threshold(cls, v: SecurityRisk) -> SecurityRisk:
        if v == SecurityRisk.UNKNOWN:
            raise ValueError("Threshold cannot be UNKNOWN")
        return v

    def should_confirm(
        self,
        risk: SecurityRisk = SecurityRisk.UNKNOWN,
        action: "ActionEvent | None" = None,
    ) -> bool:
        if risk == SecurityRisk.UNKNOWN:
            return self.confirm_unknown

        # This comparison is reflexive by default, so if the threshold is HIGH we will
        # still require confirmation for HIGH risk actions. And since the threshold is
        # guaranteed to never be UNKNOWN (by the validator), we're guaranteed to get a
        # boolean here.
        return risk.is_riskier(self.threshold)
