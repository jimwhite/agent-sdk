from typing import Literal, cast

CondensationRequestSource = Literal["agent", "environment", "user"]

CONDENSATION_REQUEST_SOURCE_VALUES: set[CondensationRequestSource] = {
    "agent",
    "environment",
    "user",
}


def check_condensation_request_source(value: str) -> CondensationRequestSource:
    if value in CONDENSATION_REQUEST_SOURCE_VALUES:
        return cast(CondensationRequestSource, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {CONDENSATION_REQUEST_SOURCE_VALUES!r}")
