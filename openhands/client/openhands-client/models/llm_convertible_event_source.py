from typing import Literal, cast

LLMConvertibleEventSource = Literal["agent", "environment", "user"]

LLM_CONVERTIBLE_EVENT_SOURCE_VALUES: set[LLMConvertibleEventSource] = {
    "agent",
    "environment",
    "user",
}


def check_llm_convertible_event_source(value: str) -> LLMConvertibleEventSource:
    if value in LLM_CONVERTIBLE_EVENT_SOURCE_VALUES:
        return cast(LLMConvertibleEventSource, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LLM_CONVERTIBLE_EVENT_SOURCE_VALUES!r}")
