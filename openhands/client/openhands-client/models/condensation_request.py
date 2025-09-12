from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.condensation_request_source import CondensationRequestSource, check_condensation_request_source
from ..types import UNSET, Unset

T = TypeVar("T", bound="CondensationRequest")


@_attrs_define
class CondensationRequest:
    """This action is used to request a condensation of the conversation history.

    Attributes:
        action (str): The action type, namely ActionType.CONDENSATION_REQUEST.

        Attributes:
            kind (str): Property to create kind field from class name when serializing.
            id (Union[Unset, str]): Unique event id (ULID/UUID)
            timestamp (Union[Unset, str]): Event timestamp
            source (Union[Unset, CondensationRequestSource]):  Default: 'environment'.
    """

    kind: str
    id: Union[Unset, str] = UNSET
    timestamp: Union[Unset, str] = UNSET
    source: Union[Unset, CondensationRequestSource] = "environment"

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
        source: Union[Unset, CondensationRequestSource]
        if isinstance(_source, Unset):
            source = UNSET
        else:
            source = check_condensation_request_source(_source)

        condensation_request = cls(
            kind=kind,
            id=id,
            timestamp=timestamp,
            source=source,
        )

        return condensation_request
