from typing import Literal, cast

MCPActionBaseSecurityRisk = Literal["HIGH", "LOW", "MEDIUM", "UNKNOWN"]

MCP_ACTION_BASE_SECURITY_RISK_VALUES: set[MCPActionBaseSecurityRisk] = {
    "HIGH",
    "LOW",
    "MEDIUM",
    "UNKNOWN",
}


def check_mcp_action_base_security_risk(value: str) -> MCPActionBaseSecurityRisk:
    if value in MCP_ACTION_BASE_SECURITY_RISK_VALUES:
        return cast(MCPActionBaseSecurityRisk, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MCP_ACTION_BASE_SECURITY_RISK_VALUES!r}")
