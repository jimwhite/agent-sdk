from pydantic import BaseModel, Field, PrivateAttr

from openhands.sdk.llm.llm_registry import RegistryEvent
from openhands.sdk.llm.utils.metrics import Metrics
from openhands.sdk.logger import get_logger


logger = get_logger(__name__)


class ConversationStats(BaseModel):
    # Public fields that will be serialized
    service_to_metrics: dict[str, Metrics] = Field(
        default_factory=dict,
        description="Active usage metrics tracked by the registry (legacy field name)",
    )

    _restored_services: set = PrivateAttr(default_factory=set)

    @property
    def usage_to_metrics(
        self,
    ) -> dict[str, Metrics]:  # pragma: no cover - compatibility shim
        return self.service_to_metrics

    def get_combined_metrics(self) -> Metrics:
        total_metrics = Metrics()
        for metrics in self.service_to_metrics.values():
            total_metrics.merge(metrics)
        return total_metrics

    def get_metrics_for_service(self, service_id: str) -> Metrics:
        if service_id not in self.service_to_metrics:
            raise Exception(f"LLM service does not exist {service_id}")

        return self.service_to_metrics[service_id]

    def get_metrics_for_usage(self, usage_id: str) -> Metrics:
        return self.get_metrics_for_service(usage_id)

    def register_llm(self, event: RegistryEvent):
        # Listen for llm creations and track their metrics
        llm = event.llm
        usage_id = llm.usage_id

        # Usage costs exist but have not been restored yet
        if (
            usage_id in self.service_to_metrics
            and usage_id not in self._restored_services
        ):
            llm.restore_metrics(self.service_to_metrics[usage_id])
            self._restored_services.add(usage_id)

        # Usage is new, track its metrics
        if usage_id not in self.service_to_metrics and llm.metrics:
            self.service_to_metrics[usage_id] = llm.metrics
