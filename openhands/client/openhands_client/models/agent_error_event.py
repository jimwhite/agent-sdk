from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define

from ..models.agent_error_event_source import AgentErrorEventSource, check_agent_error_event_source
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.metrics_snapshot import MetricsSnapshot


T = TypeVar("T", bound="AgentErrorEvent")


@_attrs_define
class AgentErrorEvent:
    """Error triggered by the agent.

    Note: This event should not contain model "thought" or "reasoning_content". It
    represents an error produced by the agent/scaffold, not model output.

        Attributes:
            error (str): The error message from the scaffold
            kind (str): Property to create kind field from class name when serializing.
            id (Union[Unset, str]): Unique event id (ULID/UUID)
            timestamp (Union[Unset, str]): Event timestamp
            source (Union[Unset, AgentErrorEventSource]):  Default: 'agent'.
            metrics (Union['MetricsSnapshot', None, Unset]): Snapshot of LLM metrics (token counts and costs). Only attached
                to the last action when multiple actions share the same LLM response.
    """

    error: str
    kind: str
    id: Union[Unset, str] = UNSET
    timestamp: Union[Unset, str] = UNSET
    source: Union[Unset, AgentErrorEventSource] = "agent"
    metrics: Union["MetricsSnapshot", None, Unset] = UNSET

    def to_dict(self) -> dict[str, Any]:
        from ..models.metrics_snapshot import MetricsSnapshot

        error = self.error

        kind = self.kind

        id = self.id

        timestamp = self.timestamp

        source: Union[Unset, str] = UNSET
        if not isinstance(self.source, Unset):
            source = self.source

        metrics: Union[None, Unset, dict[str, Any]]
        if isinstance(self.metrics, Unset):
            metrics = UNSET
        elif isinstance(self.metrics, MetricsSnapshot):
            metrics = self.metrics.to_dict()
        else:
            metrics = self.metrics

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "error": error,
                "kind": kind,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if timestamp is not UNSET:
            field_dict["timestamp"] = timestamp
        if source is not UNSET:
            field_dict["source"] = source
        if metrics is not UNSET:
            field_dict["metrics"] = metrics

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.metrics_snapshot import MetricsSnapshot

        d = dict(src_dict)
        error = d.pop("error")

        kind = d.pop("kind")

        id = d.pop("id", UNSET)

        timestamp = d.pop("timestamp", UNSET)

        _source = d.pop("source", UNSET)
        source: Union[Unset, AgentErrorEventSource]
        if isinstance(_source, Unset):
            source = UNSET
        else:
            source = check_agent_error_event_source(_source)

        def _parse_metrics(data: object) -> Union["MetricsSnapshot", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                metrics_type_0 = MetricsSnapshot.from_dict(data)

                return metrics_type_0
            except:  # noqa: E722
                pass
            return cast(Union["MetricsSnapshot", None, Unset], data)

        metrics = _parse_metrics(d.pop("metrics", UNSET))

        agent_error_event = cls(
            error=error,
            kind=kind,
            id=id,
            timestamp=timestamp,
            source=source,
            metrics=metrics,
        )

        return agent_error_event
