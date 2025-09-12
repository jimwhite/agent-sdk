from typing import Literal, cast

CondensationSource = Literal["agent", "environment", "user"]

CONDENSATION_SOURCE_VALUES: set[CondensationSource] = {
    "agent",
    "environment",
    "user",
}


def check_condensation_source(value: str) -> CondensationSource:
    if value in CONDENSATION_SOURCE_VALUES:
        return cast(CondensationSource, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {CONDENSATION_SOURCE_VALUES!r}")
