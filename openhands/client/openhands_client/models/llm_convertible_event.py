from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.llm_convertible_event_source import LLMConvertibleEventSource, check_llm_convertible_event_source
from ..types import UNSET, Unset

T = TypeVar("T", bound="LLMConvertibleEvent")


@_attrs_define
class LLMConvertibleEvent:
    """Base class for events that can be converted to LLM messages.

    Attributes:
        source (LLMConvertibleEventSource): The source of this event
        kind (str): Property to create kind field from class name when serializing.
        id (Union[Unset, str]): Unique event id (ULID/UUID)
        timestamp (Union[Unset, str]): Event timestamp
    """

    source: LLMConvertibleEventSource
    kind: str
    id: Union[Unset, str] = UNSET
    timestamp: Union[Unset, str] = UNSET

    def to_dict(self) -> dict[str, Any]:
        source: str = self.source

        kind = self.kind

        id = self.id

        timestamp = self.timestamp

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "source": source,
                "kind": kind,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if timestamp is not UNSET:
            field_dict["timestamp"] = timestamp

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        source = check_llm_convertible_event_source(d.pop("source"))

        kind = d.pop("kind")

        id = d.pop("id", UNSET)

        timestamp = d.pop("timestamp", UNSET)

        llm_convertible_event = cls(
            source=source,
            kind=kind,
            id=id,
            timestamp=timestamp,
        )

        return llm_convertible_event
