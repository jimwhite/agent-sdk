from __future__ import annotations

import shutil
import uuid
from typing import Any

import requests

from ..base import Runtime
from ..build import assemble_context_dir, tar_gz_dir
from ..models import BuildSpec


class RemoteRuntime(Runtime):
    """
    Minimal HTTP-based remote runtime.

    API (example; adapt to your server):
      POST {base_url}/build
        form-data: tag=<image-tag>
        files: context_zip=<tar.gz of full build context>
        -> { "image": "<image-tag-or-id>" }

      POST {base_url}/start
        json: {"image": "...", "name": "...", "env": {...},
            "ports": {"host": "container"}, "command": [...], "detach": true}
        -> { "container_id": "<id>" }

      POST {base_url}/stop
        json: {"container_id": "...", "remove": true}
        -> { "ok": true }
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        image: str | None = None,
        name: str | None = None,
    ):
        super().__init__(image=image, name=name)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def build(self, spec: BuildSpec) -> str:
        tag = spec.tag or f"img-{uuid.uuid4().hex[:8]}".lower()
        ctx_dir = assemble_context_dir(spec)
        try:
            payload = tar_gz_dir(ctx_dir)
        finally:
            shutil.rmtree(ctx_dir, ignore_errors=True)

        files = {"context_zip": ("context.tar.gz", payload, "application/gzip")}
        data = {"tag": tag}
        resp = requests.post(
            f"{self.base_url}/build",
            headers=self._headers(),
            data=data,
            files=files,
            timeout=600,
        )
        resp.raise_for_status()
        payload_json = resp.json()
        self.image = payload_json.get("image", tag)
        assert isinstance(self.image, str), "Image must be a string"
        return self.image

    def start(
        self,
        *,
        command: list[str] | None = None,
        env: dict[str, str] | None = None,
        ports: dict[int, int] | None = None,
        detach: bool = True,
    ) -> str:
        if not self.image:
            raise RuntimeError("No image set. Call build() first.")
        ports_json = {
            str(host): int(container) for host, container in (ports or {}).items()
        }
        data: dict[str, Any] = {
            "image": self.image,
            "name": self.name,
            "env": env or {},
            "ports": ports_json,
            "command": command or None,
            "detach": detach,
        }
        resp = requests.post(
            f"{self.base_url}/start", headers=self._headers(), json=data, timeout=120
        )
        resp.raise_for_status()
        payload = resp.json()
        self.container_id = payload.get("container_id", self.name)
        assert isinstance(self.container_id, str), "container_id must be a string"
        return self.container_id

    def stop(self, *, remove: bool = True) -> None:
        if not self.container_id and not self.name:
            return
        data = {"container_id": self.container_id or self.name, "remove": remove}
        resp = requests.post(
            f"{self.base_url}/stop", headers=self._headers(), json=data, timeout=60
        )
        resp.raise_for_status()
        self.container_id = None
