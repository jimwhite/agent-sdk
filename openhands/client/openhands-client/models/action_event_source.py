from typing import Literal, cast

ActionEventSource = Literal["agent", "environment", "user"]

ACTION_EVENT_SOURCE_VALUES: set[ActionEventSource] = {
    "agent",
    "environment",
    "user",
}


def check_action_event_source(value: str) -> ActionEventSource:
    if value in ACTION_EVENT_SOURCE_VALUES:
        return cast(ActionEventSource, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {ACTION_EVENT_SOURCE_VALUES!r}")
