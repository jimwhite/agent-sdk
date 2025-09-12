from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define

from ..models.condensation_source import CondensationSource, check_condensation_source
from ..types import UNSET, Unset

T = TypeVar("T", bound="Condensation")


@_attrs_define
class Condensation:
    """This action indicates a condensation of the conversation history is happening.

    Attributes:
        kind (str): Property to create kind field from class name when serializing.
        id (Union[Unset, str]): Unique event id (ULID/UUID)
        timestamp (Union[Unset, str]): Event timestamp
        source (Union[Unset, CondensationSource]):  Default: 'environment'.
        forgotten_event_ids (Union[None, Unset, list[str]]):
        summary (Union[None, Unset, str]):
        summary_offset (Union[None, Unset, int]):
    """

    kind: str
    id: Union[Unset, str] = UNSET
    timestamp: Union[Unset, str] = UNSET
    source: Union[Unset, CondensationSource] = "environment"
    forgotten_event_ids: Union[None, Unset, list[str]] = UNSET
    summary: Union[None, Unset, str] = UNSET
    summary_offset: Union[None, Unset, int] = UNSET

    def to_dict(self) -> dict[str, Any]:
        kind = self.kind

        id = self.id

        timestamp = self.timestamp

        source: Union[Unset, str] = UNSET
        if not isinstance(self.source, Unset):
            source = self.source

        forgotten_event_ids: Union[None, Unset, list[str]]
        if isinstance(self.forgotten_event_ids, Unset):
            forgotten_event_ids = UNSET
        elif isinstance(self.forgotten_event_ids, list):
            forgotten_event_ids = self.forgotten_event_ids

        else:
            forgotten_event_ids = self.forgotten_event_ids

        summary: Union[None, Unset, str]
        if isinstance(self.summary, Unset):
            summary = UNSET
        else:
            summary = self.summary

        summary_offset: Union[None, Unset, int]
        if isinstance(self.summary_offset, Unset):
            summary_offset = UNSET
        else:
            summary_offset = self.summary_offset

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
        if forgotten_event_ids is not UNSET:
            field_dict["forgotten_event_ids"] = forgotten_event_ids
        if summary is not UNSET:
            field_dict["summary"] = summary
        if summary_offset is not UNSET:
            field_dict["summary_offset"] = summary_offset

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        kind = d.pop("kind")

        id = d.pop("id", UNSET)

        timestamp = d.pop("timestamp", UNSET)

        _source = d.pop("source", UNSET)
        source: Union[Unset, CondensationSource]
        if isinstance(_source, Unset):
            source = UNSET
        else:
            source = check_condensation_source(_source)

        def _parse_forgotten_event_ids(data: object) -> Union[None, Unset, list[str]]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                forgotten_event_ids_type_0 = cast(list[str], data)

                return forgotten_event_ids_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, list[str]], data)

        forgotten_event_ids = _parse_forgotten_event_ids(d.pop("forgotten_event_ids", UNSET))

        def _parse_summary(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        summary = _parse_summary(d.pop("summary", UNSET))

        def _parse_summary_offset(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        summary_offset = _parse_summary_offset(d.pop("summary_offset", UNSET))

        condensation = cls(
            kind=kind,
            id=id,
            timestamp=timestamp,
            source=source,
            forgotten_event_ids=forgotten_event_ids,
            summary=summary,
            summary_offset=summary_offset,
        )

        return condensation
