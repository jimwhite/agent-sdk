from typing import Literal, cast

SendMessageRequestRole = Literal["assistant", "system", "tool", "user"]

SEND_MESSAGE_REQUEST_ROLE_VALUES: set[SendMessageRequestRole] = {
    "assistant",
    "system",
    "tool",
    "user",
}


def check_send_message_request_role(value: str) -> SendMessageRequestRole:
    if value in SEND_MESSAGE_REQUEST_ROLE_VALUES:
        return cast(SendMessageRequestRole, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SEND_MESSAGE_REQUEST_ROLE_VALUES!r}")
