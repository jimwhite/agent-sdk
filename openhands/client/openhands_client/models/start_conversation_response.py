from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.conversation_state import ConversationState


T = TypeVar("T", bound="StartConversationResponse")


@_attrs_define
class StartConversationResponse:
    """
    Attributes:
        conversation_id (str):
        state (ConversationState):
    """

    conversation_id: str
    state: "ConversationState"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        conversation_id = self.conversation_id

        state = self.state.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "conversation_id": conversation_id,
                "state": state,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.conversation_state import ConversationState

        d = dict(src_dict)
        conversation_id = d.pop("conversation_id")

        state = ConversationState.from_dict(d.pop("state"))

        start_conversation_response = cls(
            conversation_id=conversation_id,
            state=state,
        )

        start_conversation_response.additional_properties = d
        return start_conversation_response

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
