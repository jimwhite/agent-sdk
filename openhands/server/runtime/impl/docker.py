from __future__ import annotations

import shutil
import uuid
from typing import Any

import docker
from docker.errors import NotFound as DockerNotFound
from docker.models.containers import Container

from openhands.sdk import get_logger

from ..base import Runtime
from ..build import assemble_context_dir
from ..models import BuildSpec
from ..logs import LogStreamer, RollingLogger


logger = get_logger(__name__)


class DockerRuntime(Runtime):
    def __init__(
        self,
        image: str | None = None,
        name: str | None = None,
        *,
        client: docker.DockerClient | None = None,
    ):
        super().__init__(image=image, name=name)
        self.client = client or docker.from_env()
        self._container = None  # docker.models.containers.Container | None

    def _ensure_image_local(self, ref: str):
        try:
            return self.client.images.get(ref)
        except DockerNotFound:
            logger.info(f"Docker image name not found. Pulling docker image {ref}...")
            return self.client.images.pull(ref)

    def build(self, spec: BuildSpec) -> str:
        tag = spec.tag or f"img-{uuid.uuid4().hex[:8]}".lower()
        try:
            self._ensure_image_local(spec.base_image)
        except Exception:
            # non-fatal; base may still resolve during build
            pass

        ctx_dir = assemble_context_dir(spec)
        rolling = RollingLogger(max_lines=200)
        try:
            kwargs: dict[str, Any] = {
                "path": str(ctx_dir),
                "tag": tag,
                "rm": True,
                "pull": False,
                "decode": True,
            }
            if spec.build_args:
                kwargs["buildargs"] = spec.build_args
            if spec.platform:
                kwargs["platform"] = spec.platform  # requires daemon support

            # Stream build logs for better visibility
            for chunk in self.client.api.build(**kwargs):
                if isinstance(chunk, (bytes, bytearray)):
                    try:
                        chunk = chunk.decode("utf-8", errors="replace")
                    except Exception:
                        chunk = str(chunk)
                if isinstance(chunk, str):
                    rolling.add_line(chunk.rstrip())
                elif isinstance(chunk, dict):
                    # docker-py may decode JSON to dict
                    msg = chunk.get("stream") or chunk.get("status") or str(chunk)
                    rolling.add_line(str(msg).rstrip())
                else:
                    rolling.add_line(str(chunk).rstrip())
        finally:
            shutil.rmtree(ctx_dir, ignore_errors=True)

        self.image = tag
        return tag

    @staticmethod
    def _convert_ports(
        host_to_container: dict[int, int] | None,
    ) -> dict[str, int] | None:
        if not host_to_container:
            return None
        # host:container -> {"container/tcp": host}
        return {
            f"{container}/tcp": host for host, container in host_to_container.items()
        }

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

        # Remove existing container with same name to avoid conflicts
        try:
            old = self.client.containers.get(self.name)
            try:
                old.stop()
            except Exception:
                logger.warning(
                    f"Failed to stop existing container {self.name}", exc_info=True
                )
            try:
                old.remove(force=True)
            except Exception:
                logger.warning(
                    f"Failed to remove existing container {self.name}", exc_info=True
                )
        except DockerNotFound:
            pass

        container_ports = self._convert_ports(ports)
        cmd = command  # if None, image CMD applies

        self._container = self.client.containers.run(
            self.image,
            cmd,
            name=self.name,
            environment=env or {},
            ports=container_ports,
            detach=detach,
            auto_remove=False,
        )
        assert self._container is not None, "Failed to start container"
        assert isinstance(self._container, Container)
        # Start streaming logs in background for better visibility
        try:
            self._log_streamer = LogStreamer(
                self._container, lambda level, msg: logger.debug(msg)
            )
        except Exception:
            self._log_streamer = None
        assert isinstance(self._container, Container)
        self.container_id = self._container.id
        assert isinstance(self.container_id, str), "Container ID must be a string"
        return self.container_id

    def stop(self, *, remove: bool = True) -> None:
        target = self._container
        if target is None:
            try:
                target = self.client.containers.get(self.name)
            except DockerNotFound:
                self.container_id = None
                logger.info(f"No running container named {self.name} found to stop")
                return

        if not isinstance(target, Container):
            raise RuntimeError(
                "Invalid container reference. "
                f"{target} is not a docker.models.containers.Container instance."
            )
        try:
            target.stop()
        finally:
            if remove:
                try:
                    target.remove(force=True)
                except Exception:
                    logger.warning(
                        f"Failed to remove existing container {self.name}",
                        exc_info=True,
                    )
        # stop log streamer
        try:
            if hasattr(self, "_log_streamer") and self._log_streamer:
                self._log_streamer.close()
        except Exception:
            pass
        self.container_id = None
        self._container = None
