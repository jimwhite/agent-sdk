from typing import Literal, cast

ThinkActionSecurityRisk = Literal["HIGH", "LOW", "MEDIUM", "UNKNOWN"]

THINK_ACTION_SECURITY_RISK_VALUES: set[ThinkActionSecurityRisk] = {
    "HIGH",
    "LOW",
    "MEDIUM",
    "UNKNOWN",
}


def check_think_action_security_risk(value: str) -> ThinkActionSecurityRisk:
    if value in THINK_ACTION_SECURITY_RISK_VALUES:
        return cast(ThinkActionSecurityRisk, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {THINK_ACTION_SECURITY_RISK_VALUES!r}")
