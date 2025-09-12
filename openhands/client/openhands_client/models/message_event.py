from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.message_event_source import MessageEventSource, check_message_event_source
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.message import Message
    from ..models.metrics_snapshot import MetricsSnapshot
    from ..models.text_content import TextContent


T = TypeVar("T", bound="MessageEvent")


@_attrs_define
class MessageEvent:
    """Message from either agent or user.

    This is originally the "MessageAction", but it suppose not to be tool call.

        Attributes:
            source (MessageEventSource):
            llm_message (Message):
            kind (str): Property to create kind field from class name when serializing.
            reasoning_content (str):
            id (Union[Unset, str]): Unique event id (ULID/UUID)
            timestamp (Union[Unset, str]): Event timestamp
            metrics (Union['MetricsSnapshot', None, Unset]): Snapshot of LLM metrics (token counts and costs) for this
                message. Only attached to messages from agent.
            activated_microagents (Union[Unset, list[str]]): List of activated microagent name
            extended_content (Union[Unset, list['TextContent']]): List of content added by agent context
    """

    source: MessageEventSource
    llm_message: "Message"
    kind: str
    reasoning_content: str
    id: Union[Unset, str] = UNSET
    timestamp: Union[Unset, str] = UNSET
    metrics: Union["MetricsSnapshot", None, Unset] = UNSET
    activated_microagents: Union[Unset, list[str]] = UNSET
    extended_content: Union[Unset, list["TextContent"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.metrics_snapshot import MetricsSnapshot

        source: str = self.source

        llm_message = self.llm_message.to_dict()

        kind = self.kind

        reasoning_content = self.reasoning_content

        id = self.id

        timestamp = self.timestamp

        metrics: Union[None, Unset, dict[str, Any]]
        if isinstance(self.metrics, Unset):
            metrics = UNSET
        elif isinstance(self.metrics, MetricsSnapshot):
            metrics = self.metrics.to_dict()
        else:
            metrics = self.metrics

        activated_microagents: Union[Unset, list[str]] = UNSET
        if not isinstance(self.activated_microagents, Unset):
            activated_microagents = self.activated_microagents

        extended_content: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.extended_content, Unset):
            extended_content = []
            for extended_content_item_data in self.extended_content:
                extended_content_item = extended_content_item_data.to_dict()
                extended_content.append(extended_content_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "source": source,
                "llm_message": llm_message,
                "kind": kind,
                "reasoning_content": reasoning_content,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if timestamp is not UNSET:
            field_dict["timestamp"] = timestamp
        if metrics is not UNSET:
            field_dict["metrics"] = metrics
        if activated_microagents is not UNSET:
            field_dict["activated_microagents"] = activated_microagents
        if extended_content is not UNSET:
            field_dict["extended_content"] = extended_content

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.message import Message
        from ..models.metrics_snapshot import MetricsSnapshot
        from ..models.text_content import TextContent

        d = dict(src_dict)
        source = check_message_event_source(d.pop("source"))

        llm_message = Message.from_dict(d.pop("llm_message"))

        kind = d.pop("kind")

        reasoning_content = d.pop("reasoning_content")

        id = d.pop("id", UNSET)

        timestamp = d.pop("timestamp", UNSET)

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

        activated_microagents = cast(list[str], d.pop("activated_microagents", UNSET))

        extended_content = []
        _extended_content = d.pop("extended_content", UNSET)
        for extended_content_item_data in _extended_content or []:
            extended_content_item = TextContent.from_dict(extended_content_item_data)

            extended_content.append(extended_content_item)

        message_event = cls(
            source=source,
            llm_message=llm_message,
            kind=kind,
            reasoning_content=reasoning_content,
            id=id,
            timestamp=timestamp,
            metrics=metrics,
            activated_microagents=activated_microagents,
            extended_content=extended_content,
        )

        message_event.additional_properties = d
        return message_event

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
