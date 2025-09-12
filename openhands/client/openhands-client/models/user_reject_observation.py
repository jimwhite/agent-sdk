from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.user_reject_observation_source import UserRejectObservationSource, check_user_reject_observation_source
from ..types import UNSET, Unset

T = TypeVar("T", bound="UserRejectObservation")


@_attrs_define
class UserRejectObservation:
    """Observation when user rejects an action in confirmation mode.

    Attributes:
        action_id (str): The action id that this rejection is responding to
        tool_name (str): The tool name that this rejection is responding to
        tool_call_id (str): The tool call id that this rejection is responding to
        kind (str): Property to create kind field from class name when serializing.
        id (Union[Unset, str]): Unique event id (ULID/UUID)
        timestamp (Union[Unset, str]): Event timestamp
        source (Union[Unset, UserRejectObservationSource]):  Default: 'user'.
        rejection_reason (Union[Unset, str]): Reason for rejecting the action Default: 'User rejected the action'.
    """

    action_id: str
    tool_name: str
    tool_call_id: str
    kind: str
    id: Union[Unset, str] = UNSET
    timestamp: Union[Unset, str] = UNSET
    source: Union[Unset, UserRejectObservationSource] = "user"
    rejection_reason: Union[Unset, str] = "User rejected the action"

    def to_dict(self) -> dict[str, Any]:
        action_id = self.action_id

        tool_name = self.tool_name

        tool_call_id = self.tool_call_id

        kind = self.kind

        id = self.id

        timestamp = self.timestamp

        source: Union[Unset, str] = UNSET
        if not isinstance(self.source, Unset):
            source = self.source

        rejection_reason = self.rejection_reason

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
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
        if rejection_reason is not UNSET:
            field_dict["rejection_reason"] = rejection_reason

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        action_id = d.pop("action_id")

        tool_name = d.pop("tool_name")

        tool_call_id = d.pop("tool_call_id")

        kind = d.pop("kind")

        id = d.pop("id", UNSET)

        timestamp = d.pop("timestamp", UNSET)

        _source = d.pop("source", UNSET)
        source: Union[Unset, UserRejectObservationSource]
        if isinstance(_source, Unset):
            source = UNSET
        else:
            source = check_user_reject_observation_source(_source)

        rejection_reason = d.pop("rejection_reason", UNSET)

        user_reject_observation = cls(
            action_id=action_id,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            kind=kind,
            id=id,
            timestamp=timestamp,
            source=source,
            rejection_reason=rejection_reason,
        )

        return user_reject_observation
