from typing import Any, Optional

import httpx

from .exception import RemoteError


class HTTPTransport:
    """Very small HTTP wrapper used by the gateway."""

    def __init__(
        self, base_url: str, api_key: Optional[str] = None, timeout: float = 30.0
    ):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=timeout,
        )

    def request(
        self, method: str, endpoint: str, json: Optional[dict[str, Any]] = None
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        try:
            if method == "GET":
                r = self.client.get(url)
            elif method == "POST":
                r = self.client.post(url, json=json)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            r.raise_for_status()
            return r.json()
        except httpx.RequestError as e:
            raise RemoteError(f"Request failed: {e}") from e
        except httpx.HTTPStatusError as e:
            raise RemoteError(
                f"HTTP {e.response.status_code}: {e.response.text}"
            ) from e

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "HTTPTransport":
        return self

    def __exit__(self, *_args) -> None:
        self.close()
