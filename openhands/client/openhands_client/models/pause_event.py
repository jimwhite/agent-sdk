from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.pause_event_source import PauseEventSource, check_pause_event_source
from ..types import UNSET, Unset

T = TypeVar("T", bound="PauseEvent")


@_attrs_define
class PauseEvent:
    """Event indicating that the agent execution was paused by user request.

    Attributes:
        kind (str): Property to create kind field from class name when serializing.
        id (Union[Unset, str]): Unique event id (ULID/UUID)
        timestamp (Union[Unset, str]): Event timestamp
        source (Union[Unset, PauseEventSource]):  Default: 'user'.
    """

    kind: str
    id: Union[Unset, str] = UNSET
    timestamp: Union[Unset, str] = UNSET
    source: Union[Unset, PauseEventSource] = "user"

    def to_dict(self) -> dict[str, Any]:
        kind = self.kind

        id = self.id

        timestamp = self.timestamp

        source: Union[Unset, str] = UNSET
        if not isinstance(self.source, Unset):
            source = self.source

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
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
        d = dict(src_dict)
        kind = d.pop("kind")

        id = d.pop("id", UNSET)

        timestamp = d.pop("timestamp", UNSET)

        _source = d.pop("source", UNSET)
        source: Union[Unset, PauseEventSource]
        if isinstance(_source, Unset):
            source = UNSET
        else:
            source = check_pause_event_source(_source)

        pause_event = cls(
            kind=kind,
            id=id,
            timestamp=timestamp,
            source=source,
        )

        return pause_event
