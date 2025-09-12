from typing import Literal, cast

FinishActionSecurityRisk = Literal["HIGH", "LOW", "MEDIUM", "UNKNOWN"]

FINISH_ACTION_SECURITY_RISK_VALUES: set[FinishActionSecurityRisk] = {
    "HIGH",
    "LOW",
    "MEDIUM",
    "UNKNOWN",
}


def check_finish_action_security_risk(value: str) -> FinishActionSecurityRisk:
    if value in FINISH_ACTION_SECURITY_RISK_VALUES:
        return cast(FinishActionSecurityRisk, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {FINISH_ACTION_SECURITY_RISK_VALUES!r}")
