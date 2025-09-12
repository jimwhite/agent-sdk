from typing import Literal, cast

LLMReasoningEffortType0 = Literal["high", "low", "medium", "none"]

LLM_REASONING_EFFORT_TYPE_0_VALUES: set[LLMReasoningEffortType0] = {
    "high",
    "low",
    "medium",
    "none",
}


def check_llm_reasoning_effort_type_0(value: str) -> LLMReasoningEffortType0:
    if value in LLM_REASONING_EFFORT_TYPE_0_VALUES:
        return cast(LLMReasoningEffortType0, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LLM_REASONING_EFFORT_TYPE_0_VALUES!r}")
