from typing import Literal, cast

UserRejectObservationSource = Literal["agent", "environment", "user"]

USER_REJECT_OBSERVATION_SOURCE_VALUES: set[UserRejectObservationSource] = {
    "agent",
    "environment",
    "user",
}


def check_user_reject_observation_source(value: str) -> UserRejectObservationSource:
    if value in USER_REJECT_OBSERVATION_SOURCE_VALUES:
        return cast(UserRejectObservationSource, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {USER_REJECT_OBSERVATION_SOURCE_VALUES!r}")
