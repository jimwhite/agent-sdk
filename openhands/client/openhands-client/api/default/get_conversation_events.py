from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.action_event import ActionEvent
from ...models.agent_error_event import AgentErrorEvent
from ...models.condensation import Condensation
from ...models.condensation_request import CondensationRequest
from ...models.http_validation_error import HTTPValidationError
from ...models.llm_convertible_event import LLMConvertibleEvent
from ...models.message_event import MessageEvent
from ...models.observation_event import ObservationEvent
from ...models.pause_event import PauseEvent
from ...models.system_prompt_event import SystemPromptEvent
from ...models.user_reject_observation import UserRejectObservation
from ...types import UNSET, Response, Unset


def _get_kwargs(
    conversation_id: str,
    *,
    start: Union[Unset, int] = 0,
    limit: Union[Unset, int] = 100,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["start"] = start

    params["limit"] = limit

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/conversations/{conversation_id}/events",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[
        HTTPValidationError,
        list[
            Union[
                "ActionEvent",
                "AgentErrorEvent",
                "Condensation",
                "CondensationRequest",
                "LLMConvertibleEvent",
                "MessageEvent",
                "ObservationEvent",
                "PauseEvent",
                "SystemPromptEvent",
                "UserRejectObservation",
            ]
        ],
    ]
]:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:

            def _parse_response_200_item(
                data: object,
            ) -> Union[
                "ActionEvent",
                "AgentErrorEvent",
                "Condensation",
                "CondensationRequest",
                "LLMConvertibleEvent",
                "MessageEvent",
                "ObservationEvent",
                "PauseEvent",
                "SystemPromptEvent",
                "UserRejectObservation",
            ]:
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_0 = LLMConvertibleEvent.from_dict(data)

                    return response_200_item_type_0
                except:  # noqa: E722
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_1 = Condensation.from_dict(data)

                    return response_200_item_type_1
                except:  # noqa: E722
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_2 = CondensationRequest.from_dict(data)

                    return response_200_item_type_2
                except:  # noqa: E722
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_3 = PauseEvent.from_dict(data)

                    return response_200_item_type_3
                except:  # noqa: E722
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_4 = SystemPromptEvent.from_dict(data)

                    return response_200_item_type_4
                except:  # noqa: E722
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_5 = ActionEvent.from_dict(data)

                    return response_200_item_type_5
                except:  # noqa: E722
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_6 = ObservationEvent.from_dict(data)

                    return response_200_item_type_6
                except:  # noqa: E722
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_7 = MessageEvent.from_dict(data)

                    return response_200_item_type_7
                except:  # noqa: E722
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_8 = UserRejectObservation.from_dict(data)

                    return response_200_item_type_8
                except:  # noqa: E722
                    pass
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_item_type_9 = AgentErrorEvent.from_dict(data)

                return response_200_item_type_9

            response_200_item = _parse_response_200_item(response_200_item_data)

            response_200.append(response_200_item)

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[
        HTTPValidationError,
        list[
            Union[
                "ActionEvent",
                "AgentErrorEvent",
                "Condensation",
                "CondensationRequest",
                "LLMConvertibleEvent",
                "MessageEvent",
                "ObservationEvent",
                "PauseEvent",
                "SystemPromptEvent",
                "UserRejectObservation",
            ]
        ],
    ]
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    conversation_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    start: Union[Unset, int] = 0,
    limit: Union[Unset, int] = 100,
) -> Response[
    Union[
        HTTPValidationError,
        list[
            Union[
                "ActionEvent",
                "AgentErrorEvent",
                "Condensation",
                "CondensationRequest",
                "LLMConvertibleEvent",
                "MessageEvent",
                "ObservationEvent",
                "PauseEvent",
                "SystemPromptEvent",
                "UserRejectObservation",
            ]
        ],
    ]
]:
    """Get Events

     Retrieves the event history for a conversation with pagination.

    Args:
        conversation_id (str):
        start (Union[Unset, int]):  Default: 0.
        limit (Union[Unset, int]):  Default: 100.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, list[Union['ActionEvent', 'AgentErrorEvent', 'Condensation', 'CondensationRequest', 'LLMConvertibleEvent', 'MessageEvent', 'ObservationEvent', 'PauseEvent', 'SystemPromptEvent', 'UserRejectObservation']]]]
    """

    kwargs = _get_kwargs(
        conversation_id=conversation_id,
        start=start,
        limit=limit,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    conversation_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    start: Union[Unset, int] = 0,
    limit: Union[Unset, int] = 100,
) -> Optional[
    Union[
        HTTPValidationError,
        list[
            Union[
                "ActionEvent",
                "AgentErrorEvent",
                "Condensation",
                "CondensationRequest",
                "LLMConvertibleEvent",
                "MessageEvent",
                "ObservationEvent",
                "PauseEvent",
                "SystemPromptEvent",
                "UserRejectObservation",
            ]
        ],
    ]
]:
    """Get Events

     Retrieves the event history for a conversation with pagination.

    Args:
        conversation_id (str):
        start (Union[Unset, int]):  Default: 0.
        limit (Union[Unset, int]):  Default: 100.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, list[Union['ActionEvent', 'AgentErrorEvent', 'Condensation', 'CondensationRequest', 'LLMConvertibleEvent', 'MessageEvent', 'ObservationEvent', 'PauseEvent', 'SystemPromptEvent', 'UserRejectObservation']]]
    """

    return sync_detailed(
        conversation_id=conversation_id,
        client=client,
        start=start,
        limit=limit,
    ).parsed


async def asyncio_detailed(
    conversation_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    start: Union[Unset, int] = 0,
    limit: Union[Unset, int] = 100,
) -> Response[
    Union[
        HTTPValidationError,
        list[
            Union[
                "ActionEvent",
                "AgentErrorEvent",
                "Condensation",
                "CondensationRequest",
                "LLMConvertibleEvent",
                "MessageEvent",
                "ObservationEvent",
                "PauseEvent",
                "SystemPromptEvent",
                "UserRejectObservation",
            ]
        ],
    ]
]:
    """Get Events

     Retrieves the event history for a conversation with pagination.

    Args:
        conversation_id (str):
        start (Union[Unset, int]):  Default: 0.
        limit (Union[Unset, int]):  Default: 100.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, list[Union['ActionEvent', 'AgentErrorEvent', 'Condensation', 'CondensationRequest', 'LLMConvertibleEvent', 'MessageEvent', 'ObservationEvent', 'PauseEvent', 'SystemPromptEvent', 'UserRejectObservation']]]]
    """

    kwargs = _get_kwargs(
        conversation_id=conversation_id,
        start=start,
        limit=limit,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    conversation_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    start: Union[Unset, int] = 0,
    limit: Union[Unset, int] = 100,
) -> Optional[
    Union[
        HTTPValidationError,
        list[
            Union[
                "ActionEvent",
                "AgentErrorEvent",
                "Condensation",
                "CondensationRequest",
                "LLMConvertibleEvent",
                "MessageEvent",
                "ObservationEvent",
                "PauseEvent",
                "SystemPromptEvent",
                "UserRejectObservation",
            ]
        ],
    ]
]:
    """Get Events

     Retrieves the event history for a conversation with pagination.

    Args:
        conversation_id (str):
        start (Union[Unset, int]):  Default: 0.
        limit (Union[Unset, int]):  Default: 100.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, list[Union['ActionEvent', 'AgentErrorEvent', 'Condensation', 'CondensationRequest', 'LLMConvertibleEvent', 'MessageEvent', 'ObservationEvent', 'PauseEvent', 'SystemPromptEvent', 'UserRejectObservation']]]
    """

    return (
        await asyncio_detailed(
            conversation_id=conversation_id,
            client=client,
            start=start,
            limit=limit,
        )
    ).parsed
