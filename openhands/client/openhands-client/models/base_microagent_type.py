from typing import Literal, cast

BaseMicroagentType = Literal["knowledge", "repo", "task"]

BASE_MICROAGENT_TYPE_VALUES: set[BaseMicroagentType] = {
    "knowledge",
    "repo",
    "task",
}


def check_base_microagent_type(value: str) -> BaseMicroagentType:
    if value in BASE_MICROAGENT_TYPE_VALUES:
        return cast(BaseMicroagentType, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {BASE_MICROAGENT_TYPE_VALUES!r}")
