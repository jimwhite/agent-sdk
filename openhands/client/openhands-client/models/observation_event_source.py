from typing import Literal, cast

ObservationEventSource = Literal["agent", "environment", "user"]

OBSERVATION_EVENT_SOURCE_VALUES: set[ObservationEventSource] = {
    "agent",
    "environment",
    "user",
}


def check_observation_event_source(value: str) -> ObservationEventSource:
    if value in OBSERVATION_EVENT_SOURCE_VALUES:
        return cast(ObservationEventSource, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {OBSERVATION_EVENT_SOURCE_VALUES!r}")
