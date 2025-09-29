from openhands.sdk.event import ActionEvent
from openhands.sdk.logger import get_logger
from openhands.sdk.security.analyzer import SecurityAnalyzerBase
from openhands.sdk.security.risk import SecurityRisk


logger = get_logger(__name__)


class DefaultSecurityAnalyzer(SecurityAnalyzerBase):
    """Default security analyzer that always returns UNKNOWN risk.

    This analyzer provides a simple default implementation that always returns
    SecurityRisk.UNKNOWN for any action. It serves as a fallback when no specific
    security analysis is needed but a security analyzer is required.
    """

    def security_risk(self, action: ActionEvent) -> SecurityRisk:
        """Always return UNKNOWN security risk.

        Args:
            action: The ActionEvent to analyze (ignored)

        Returns:
            SecurityRisk.UNKNOWN for all actions
        """
        logger.debug(f"Default analyzer returning UNKNOWN risk for action: {action}")
        return SecurityRisk.UNKNOWN
