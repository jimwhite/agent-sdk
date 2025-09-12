from typing import Literal, cast

SystemPromptEventSource = Literal["agent", "environment", "user"]

SYSTEM_PROMPT_EVENT_SOURCE_VALUES: set[SystemPromptEventSource] = {
    "agent",
    "environment",
    "user",
}


def check_system_prompt_event_source(value: str) -> SystemPromptEventSource:
    if value in SYSTEM_PROMPT_EVENT_SOURCE_VALUES:
        return cast(SystemPromptEventSource, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SYSTEM_PROMPT_EVENT_SOURCE_VALUES!r}")
