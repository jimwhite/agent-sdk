from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.agent_base import AgentBase


T = TypeVar("T", bound="ConversationState")


@_attrs_define
class ConversationState:
    """
    Attributes:
        id (str): Unique conversation ID
        agent (AgentBase):
        agent_finished (Union[Unset, bool]):  Default: False.
        confirmation_mode (Union[Unset, bool]):  Default: False.
        agent_waiting_for_confirmation (Union[Unset, bool]):  Default: False.
        agent_paused (Union[Unset, bool]):  Default: False.
        activated_knowledge_microagents (Union[Unset, list[str]]): List of activated knowledge microagents name
    """

    id: str
    agent: "AgentBase"
    agent_finished: Union[Unset, bool] = False
    confirmation_mode: Union[Unset, bool] = False
    agent_waiting_for_confirmation: Union[Unset, bool] = False
    agent_paused: Union[Unset, bool] = False
    activated_knowledge_microagents: Union[Unset, list[str]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        agent = self.agent.to_dict()

        agent_finished = self.agent_finished

        confirmation_mode = self.confirmation_mode

        agent_waiting_for_confirmation = self.agent_waiting_for_confirmation

        agent_paused = self.agent_paused

        activated_knowledge_microagents: Union[Unset, list[str]] = UNSET
        if not isinstance(self.activated_knowledge_microagents, Unset):
            activated_knowledge_microagents = self.activated_knowledge_microagents

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "agent": agent,
            }
        )
        if agent_finished is not UNSET:
            field_dict["agent_finished"] = agent_finished
        if confirmation_mode is not UNSET:
            field_dict["confirmation_mode"] = confirmation_mode
        if agent_waiting_for_confirmation is not UNSET:
            field_dict["agent_waiting_for_confirmation"] = agent_waiting_for_confirmation
        if agent_paused is not UNSET:
            field_dict["agent_paused"] = agent_paused
        if activated_knowledge_microagents is not UNSET:
            field_dict["activated_knowledge_microagents"] = activated_knowledge_microagents

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.agent_base import AgentBase

        d = dict(src_dict)
        id = d.pop("id")

        agent = AgentBase.from_dict(d.pop("agent"))

        agent_finished = d.pop("agent_finished", UNSET)

        confirmation_mode = d.pop("confirmation_mode", UNSET)

        agent_waiting_for_confirmation = d.pop("agent_waiting_for_confirmation", UNSET)

        agent_paused = d.pop("agent_paused", UNSET)

        activated_knowledge_microagents = cast(list[str], d.pop("activated_knowledge_microagents", UNSET))

        conversation_state = cls(
            id=id,
            agent=agent,
            agent_finished=agent_finished,
            confirmation_mode=confirmation_mode,
            agent_waiting_for_confirmation=agent_waiting_for_confirmation,
            agent_paused=agent_paused,
            activated_knowledge_microagents=activated_knowledge_microagents,
        )

        conversation_state.additional_properties = d
        return conversation_state

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
