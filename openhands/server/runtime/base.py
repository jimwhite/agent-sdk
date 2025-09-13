from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from .models import BuildSpec


class Runtime(ABC):
    def __init__(self, image: str | None = None, name: str | None = None):
        self.image: str | None = image
        self.name: str = name or f"rk-{uuid.uuid4().hex[:8]}"
        self.container_id: str | None = None

    @abstractmethod
    def build(self, spec: BuildSpec) -> str:
        """Build an image defined by BuildSpec and return the image tag."""
        raise NotImplementedError

    @abstractmethod
    def start(
        self,
        *,
        command: list[str] | None = None,
        env: dict[str, str] | None = None,
        ports: dict[int, int] | None = None,  # host_port -> container_port
        detach: bool = True,
    ) -> str:
        """Start the container and return the container id/handle."""
        raise NotImplementedError

    @abstractmethod
    def stop(self, *, remove: bool = True) -> None:
        """Stop the running container (if any). If remove=True, also remove it."""
        raise NotImplementedError
