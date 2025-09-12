from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.observation_event_source import ObservationEventSource, check_observation_event_source
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.finish_observation import FinishObservation
    from ..models.think_observation import ThinkObservation


T = TypeVar("T", bound="ObservationEvent")


@_attrs_define
class ObservationEvent:
    """
    Attributes:
        observation (Union['FinishObservation', 'ThinkObservation']): The observation (tool call) sent to LLM
        action_id (str): The action id that this observation is responding to
        tool_name (str): The tool name that this observation is responding to
        tool_call_id (str): The tool call id that this observation is responding to
        kind (str): Property to create kind field from class name when serializing.
        id (Union[Unset, str]): Unique event id (ULID/UUID)
        timestamp (Union[Unset, str]): Event timestamp
        source (Union[Unset, ObservationEventSource]):  Default: 'environment'.
    """

    observation: Union["FinishObservation", "ThinkObservation"]
    action_id: str
    tool_name: str
    tool_call_id: str
    kind: str
    id: Union[Unset, str] = UNSET
    timestamp: Union[Unset, str] = UNSET
    source: Union[Unset, ObservationEventSource] = "environment"

    def to_dict(self) -> dict[str, Any]:
        from ..models.finish_observation import FinishObservation

        observation: dict[str, Any]
        if isinstance(self.observation, FinishObservation):
            observation = self.observation.to_dict()
        else:
            observation = self.observation.to_dict()

        action_id = self.action_id

        tool_name = self.tool_name

        tool_call_id = self.tool_call_id

        kind = self.kind

        id = self.id

        timestamp = self.timestamp

        source: Union[Unset, str] = UNSET
        if not isinstance(self.source, Unset):
            source = self.source

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "observation": observation,
                "action_id": action_id,
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "kind": kind,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if timestamp is not UNSET:
            field_dict["timestamp"] = timestamp
        if source is not UNSET:
            field_dict["source"] = source

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.finish_observation import FinishObservation
        from ..models.think_observation import ThinkObservation

        d = dict(src_dict)

        def _parse_observation(data: object) -> Union["FinishObservation", "ThinkObservation"]:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                observation_type_0 = FinishObservation.from_dict(data)

                return observation_type_0
            except:  # noqa: E722
                pass
            if not isinstance(data, dict):
                raise TypeError()
            observation_type_1 = ThinkObservation.from_dict(data)

            return observation_type_1

        observation = _parse_observation(d.pop("observation"))

        action_id = d.pop("action_id")

        tool_name = d.pop("tool_name")

        tool_call_id = d.pop("tool_call_id")

        kind = d.pop("kind")

        id = d.pop("id", UNSET)

        timestamp = d.pop("timestamp", UNSET)

        _source = d.pop("source", UNSET)
        source: Union[Unset, ObservationEventSource]
        if isinstance(_source, Unset):
            source = UNSET
        else:
            source = check_observation_event_source(_source)

        observation_event = cls(
            observation=observation,
            action_id=action_id,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            kind=kind,
            id=id,
            timestamp=timestamp,
            source=source,
        )

        return observation_event
