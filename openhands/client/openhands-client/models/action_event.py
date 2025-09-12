from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define

from ..models.action_event_source import ActionEventSource, check_action_event_source
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.chat_completion_message_tool_call import ChatCompletionMessageToolCall
    from ..models.finish_action import FinishAction
    from ..models.mcp_action_base import MCPActionBase
    from ..models.metrics_snapshot import MetricsSnapshot
    from ..models.text_content import TextContent
    from ..models.think_action import ThinkAction


T = TypeVar("T", bound="ActionEvent")


@_attrs_define
class ActionEvent:
    """
    Attributes:
        thought (list['TextContent']): The thought process of the agent before taking this action
        action (Union['FinishAction', 'MCPActionBase', 'ThinkAction']): Single action (tool call) returned by LLM
        tool_name (str): The name of the tool being called
        tool_call_id (str): The unique id returned by LLM API for this tool call
        tool_call (ChatCompletionMessageToolCall):
        llm_response_id (str): Groups related actions from same LLM response. This helps in tracking and managing
            results of parallel function calling from the same LLM response.
        kind (str): Property to create kind field from class name when serializing.
        id (Union[Unset, str]): Unique event id (ULID/UUID)
        timestamp (Union[Unset, str]): Event timestamp
        source (Union[Unset, ActionEventSource]):  Default: 'agent'.
        reasoning_content (Union[None, Unset, str]): Intermediate reasoning/thinking content from reasoning models
        metrics (Union['MetricsSnapshot', None, Unset]): Snapshot of LLM metrics (token counts and costs). Only attached
            to the last action when multiple actions share the same LLM response.
    """

    thought: list["TextContent"]
    action: Union["FinishAction", "MCPActionBase", "ThinkAction"]
    tool_name: str
    tool_call_id: str
    tool_call: "ChatCompletionMessageToolCall"
    llm_response_id: str
    kind: str
    id: Union[Unset, str] = UNSET
    timestamp: Union[Unset, str] = UNSET
    source: Union[Unset, ActionEventSource] = "agent"
    reasoning_content: Union[None, Unset, str] = UNSET
    metrics: Union["MetricsSnapshot", None, Unset] = UNSET

    def to_dict(self) -> dict[str, Any]:
        from ..models.finish_action import FinishAction
        from ..models.mcp_action_base import MCPActionBase
        from ..models.metrics_snapshot import MetricsSnapshot

        thought = []
        for thought_item_data in self.thought:
            thought_item = thought_item_data.to_dict()
            thought.append(thought_item)

        action: dict[str, Any]
        if isinstance(self.action, MCPActionBase):
            action = self.action.to_dict()
        elif isinstance(self.action, FinishAction):
            action = self.action.to_dict()
        else:
            action = self.action.to_dict()

        tool_name = self.tool_name

        tool_call_id = self.tool_call_id

        tool_call = self.tool_call.to_dict()

        llm_response_id = self.llm_response_id

        kind = self.kind

        id = self.id

        timestamp = self.timestamp

        source: Union[Unset, str] = UNSET
        if not isinstance(self.source, Unset):
            source = self.source

        reasoning_content: Union[None, Unset, str]
        if isinstance(self.reasoning_content, Unset):
            reasoning_content = UNSET
        else:
            reasoning_content = self.reasoning_content

        metrics: Union[None, Unset, dict[str, Any]]
        if isinstance(self.metrics, Unset):
            metrics = UNSET
        elif isinstance(self.metrics, MetricsSnapshot):
            metrics = self.metrics.to_dict()
        else:
            metrics = self.metrics

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "thought": thought,
                "action": action,
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "tool_call": tool_call,
                "llm_response_id": llm_response_id,
                "kind": kind,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if timestamp is not UNSET:
            field_dict["timestamp"] = timestamp
        if source is not UNSET:
            field_dict["source"] = source
        if reasoning_content is not UNSET:
            field_dict["reasoning_content"] = reasoning_content
        if metrics is not UNSET:
            field_dict["metrics"] = metrics

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.chat_completion_message_tool_call import ChatCompletionMessageToolCall
        from ..models.finish_action import FinishAction
        from ..models.mcp_action_base import MCPActionBase
        from ..models.metrics_snapshot import MetricsSnapshot
        from ..models.text_content import TextContent
        from ..models.think_action import ThinkAction

        d = dict(src_dict)
        thought = []
        _thought = d.pop("thought")
        for thought_item_data in _thought:
            thought_item = TextContent.from_dict(thought_item_data)

            thought.append(thought_item)

        def _parse_action(data: object) -> Union["FinishAction", "MCPActionBase", "ThinkAction"]:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                action_type_0 = MCPActionBase.from_dict(data)

                return action_type_0
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                action_type_1 = FinishAction.from_dict(data)

                return action_type_1
            except:  # noqa: E722
                pass
            if not isinstance(data, dict):
                raise TypeError()
            action_type_2 = ThinkAction.from_dict(data)

            return action_type_2

        action = _parse_action(d.pop("action"))

        tool_name = d.pop("tool_name")

        tool_call_id = d.pop("tool_call_id")

        tool_call = ChatCompletionMessageToolCall.from_dict(d.pop("tool_call"))

        llm_response_id = d.pop("llm_response_id")

        kind = d.pop("kind")

        id = d.pop("id", UNSET)

        timestamp = d.pop("timestamp", UNSET)

        _source = d.pop("source", UNSET)
        source: Union[Unset, ActionEventSource]
        if isinstance(_source, Unset):
            source = UNSET
        else:
            source = check_action_event_source(_source)

        def _parse_reasoning_content(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        reasoning_content = _parse_reasoning_content(d.pop("reasoning_content", UNSET))

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

        action_event = cls(
            thought=thought,
            action=action,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            tool_call=tool_call,
            llm_response_id=llm_response_id,
            kind=kind,
            id=id,
            timestamp=timestamp,
            source=source,
            reasoning_content=reasoning_content,
            metrics=metrics,
        )

        return action_event
