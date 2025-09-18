from openhands.sdk.logger import get_logger
from openhands.sdk.security.analyzer import SecurityAnalyzer
from openhands.sdk.security.risk import SecurityRisk
from openhands.sdk.tool.schema import SchemaInstance


logger = get_logger(__name__)


class LLMSecurityAnalyzer(SecurityAnalyzer):
    """LLM-based security analyzer.

    This analyzer respects the security_risk attribute that can be set by the LLM
    when generating actions, similar to OpenHands' LLMRiskAnalyzer.

    It provides a lightweight security analysis approach that leverages the LLM's
    understanding of action context and potential risks.
    """

    def security_risk(self, action: SchemaInstance) -> SecurityRisk:
        """Evaluate security risk based on LLM-provided assessment.

        This method checks if the action has a security_risk attribute set by the LLM
        and returns it. The LLM may not always provide this attribute but it defaults to
        UNKNOWN if not explicitly set.
        """
        risk_value = action.data.get("security_risk", SecurityRisk.UNKNOWN.value)

        try:
            normalized = SecurityRisk(risk_value)
        except ValueError:
            logger.debug(
                "Unknown security risk %s provided by action %s; defaulting to UNKNOWN",
                risk_value,
                action.name,
            )
            normalized = SecurityRisk.UNKNOWN

        logger.debug("Analyzing security risk: %s -- %s", action.name, normalized)

        return normalized
