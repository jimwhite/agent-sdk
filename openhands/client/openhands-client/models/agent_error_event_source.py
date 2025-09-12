from typing import Literal, cast

AgentErrorEventSource = Literal["agent", "environment", "user"]

AGENT_ERROR_EVENT_SOURCE_VALUES: set[AgentErrorEventSource] = {
    "agent",
    "environment",
    "user",
}


def check_agent_error_event_source(value: str) -> AgentErrorEventSource:
    if value in AGENT_ERROR_EVENT_SOURCE_VALUES:
        return cast(AgentErrorEventSource, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {AGENT_ERROR_EVENT_SOURCE_VALUES!r}")
