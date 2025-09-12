from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.base_microagent import BaseMicroagent


T = TypeVar("T", bound="AgentContext")


@_attrs_define
class AgentContext:
    """Central structure for managing prompt extension.

    AgentContext unifies all the contextual inputs that shape how the system
    extends and interprets user prompts. It combines both static environment
    details and dynamic, user-activated extensions from microagents.

    Specifically, it provides:
    - **Repository context / Repo Microagents**: Information about the active codebase,
      branches, and repo-specific instructions contributed by repo microagents.
    - **Runtime context**: Current execution environment (hosts, working
      directory, secrets, date, etc.).
    - **Conversation instructions**: Optional task- or channel-specific rules
      that constrain or guide the agent’s behavior across the session.
    - **Knowledge Microagents**: Extensible components that can be triggered by user input
      to inject knowledge or domain-specific guidance.

    Together, these elements make AgentContext the primary container responsible
    for assembling, formatting, and injecting all prompt-relevant context into
    LLM interactions.

        Attributes:
            microagents (Union[Unset, list['BaseMicroagent']]): List of available microagents that can extend the user's
                input.
            system_message_suffix (Union[None, Unset, str]): Optional suffix to append to the system prompt.
            user_message_suffix (Union[None, Unset, str]): Optional suffix to append to the user's message.
    """

    microagents: Union[Unset, list["BaseMicroagent"]] = UNSET
    system_message_suffix: Union[None, Unset, str] = UNSET
    user_message_suffix: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        microagents: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.microagents, Unset):
            microagents = []
            for microagents_item_data in self.microagents:
                microagents_item = microagents_item_data.to_dict()
                microagents.append(microagents_item)

        system_message_suffix: Union[None, Unset, str]
        if isinstance(self.system_message_suffix, Unset):
            system_message_suffix = UNSET
        else:
            system_message_suffix = self.system_message_suffix

        user_message_suffix: Union[None, Unset, str]
        if isinstance(self.user_message_suffix, Unset):
            user_message_suffix = UNSET
        else:
            user_message_suffix = self.user_message_suffix

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if microagents is not UNSET:
            field_dict["microagents"] = microagents
        if system_message_suffix is not UNSET:
            field_dict["system_message_suffix"] = system_message_suffix
        if user_message_suffix is not UNSET:
            field_dict["user_message_suffix"] = user_message_suffix

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.base_microagent import BaseMicroagent

        d = dict(src_dict)
        microagents = []
        _microagents = d.pop("microagents", UNSET)
        for microagents_item_data in _microagents or []:
            microagents_item = BaseMicroagent.from_dict(microagents_item_data)

            microagents.append(microagents_item)

        def _parse_system_message_suffix(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        system_message_suffix = _parse_system_message_suffix(d.pop("system_message_suffix", UNSET))

        def _parse_user_message_suffix(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        user_message_suffix = _parse_user_message_suffix(d.pop("user_message_suffix", UNSET))

        agent_context = cls(
            microagents=microagents,
            system_message_suffix=system_message_suffix,
            user_message_suffix=user_message_suffix,
        )

        agent_context.additional_properties = d
        return agent_context

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
