from typing import Literal, cast

PauseEventSource = Literal["agent", "environment", "user"]

PAUSE_EVENT_SOURCE_VALUES: set[PauseEventSource] = {
    "agent",
    "environment",
    "user",
}


def check_pause_event_source(value: str) -> PauseEventSource:
    if value in PAUSE_EVENT_SOURCE_VALUES:
        return cast(PauseEventSource, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PAUSE_EVENT_SOURCE_VALUES!r}")
