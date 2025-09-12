from typing import Literal, cast

MessageEventSource = Literal["agent", "environment", "user"]

MESSAGE_EVENT_SOURCE_VALUES: set[MessageEventSource] = {
    "agent",
    "environment",
    "user",
}


def check_message_event_source(value: str) -> MessageEventSource:
    if value in MESSAGE_EVENT_SOURCE_VALUES:
        return cast(MessageEventSource, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MESSAGE_EVENT_SOURCE_VALUES!r}")
