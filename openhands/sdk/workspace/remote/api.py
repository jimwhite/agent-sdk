"""API-based remote workspace implementation using runtime API."""

import base64
import time
from typing import Any
from urllib.request import urlopen

import httpx
import tenacity
from pydantic import Field, PrivateAttr

from openhands.sdk.logger import get_logger
from openhands.sdk.workspace.build_utils import (
    create_agent_server_build_context_tarball,
)
from openhands.sdk.workspace.remote.base import RemoteWorkspace


logger = get_logger(__name__)


class APIRemoteWorkspace(RemoteWorkspace):
    """Remote workspace using OpenHands runtime API.

    Example:
        workspace = APIRemoteWorkspace(
            api_url="https://runtime.eval.all-hands.dev",
            runtime_api_key="your-api-key",
            base_image="nikolaik/python-nodejs:python3.12-nodejs22",
            build_agent_server=True,  # Auto-builds agent-server
            registry_prefix="gcr.io/project/repo",
        )
    """  # noqa: E501

    api_url: str = Field(description="Base URL of the runtime API")
    runtime_api_key: str = Field(description="API key for authentication")
    base_image: str = Field(description="Base container image")
    session_id: str | None = Field(
        default=None, description="Session ID (auto-generated if None)"
    )
    resource_factor: int = Field(
        default=1, description="Resource scaling (1, 2, 4, or 8)"
    )
    runtime_class: str | None = Field(
        default=None, description="Runtime class (e.g., 'sysbox')"
    )
    init_timeout: float = Field(
        default=300.0, description="Runtime init timeout (seconds)"
    )
    api_timeout: float = Field(
        default=60.0, description="API request timeout (seconds)"
    )
    build_timeout: float = Field(default=1800.0, description="Build timeout (seconds)")
    keep_alive: bool = Field(default=False, description="Keep runtime alive on cleanup")
    pause_on_close: bool = Field(
        default=False, description="Pause instead of stop on cleanup"
    )
    build_agent_server: bool = Field(
        default=False, description="Auto-build agent-server"
    )
    registry_prefix: str | None = Field(
        default=None, description="Registry prefix for built images"
    )
    build_variant: str = Field(
        default="python", description="Agent-server variant (python/java/golang)"
    )
    build_target: str = Field(
        default="binary", description="Build target (binary/source)"
    )
    build_context_path: str | None = Field(
        default=None, repr=False, description="[Advanced] Build context path"
    )
    build_tags: list[str] | None = Field(
        default=None, repr=False, description="[Advanced] Image tags"
    )
    host: str = Field(
        default="", exclude=True, repr=False, description="[Internal] Runtime URL"
    )

    _runtime_id: str | None = PrivateAttr(default=None)
    _runtime_url: str | None = PrivateAttr(default=None)
    _session_api_key: str | None = PrivateAttr(default=None)
    _api_session: httpx.Client = PrivateAttr()
    _build_config: Any = PrivateAttr(default=None)

    def model_post_init(self, context: Any) -> None:
        """Set up the remote runtime and initialize the workspace."""
        if self.session_id is None:
            object.__setattr__(self, "session_id", f"agent-server-{int(time.time())}")

        if self.resource_factor not in [1, 2, 4, 8]:
            raise ValueError(
                f"resource_factor must be 1, 2, 4, or 8, got {self.resource_factor}"
            )

        self._api_session = httpx.Client(
            headers={"X-API-Key": self.runtime_api_key}, timeout=self.api_timeout
        )
        object.__setattr__(self, "api_url", self.api_url.rstrip("/"))

        if self.build_agent_server:
            self._setup_agent_server_build()

        if self.build_context_path:
            # Check if image already exists before building
            primary_tag = (self.build_tags or [self.base_image])[0]
            if self.registry_prefix and not primary_tag.startswith(
                self.registry_prefix
            ):
                check_tag = f"{self.registry_prefix}/{primary_tag}"
            else:
                check_tag = primary_tag

            image_exists = False
            try:
                logger.info("Checking if image exists: %s", check_tag)
                image_exists = self.image_exists(check_tag)
                if image_exists:
                    logger.info("Image already exists, skipping build: %s", check_tag)
                    object.__setattr__(self, "base_image", check_tag)
            except Exception as e:
                logger.warning(
                    f"Could not check if image exists: {e}, will attempt build"
                )

            if not image_exists:
                logger.info("Building image from: %s", self.build_context_path)
                built_image = self.build_image_via_api(
                    path=self.build_context_path,
                    tags=self.build_tags or [self.base_image],
                )
                logger.info("Built image: %s", built_image)
                object.__setattr__(self, "base_image", built_image)

        try:
            self._start_or_attach_to_runtime()
            logger.info("Runtime ready at %s", self.host)
            super().model_post_init(context)
        except Exception:
            self.cleanup()
            raise

    def _setup_agent_server_build(self) -> None:
        """Auto-configure build settings for agent-server image."""
        from openhands.sdk.workspace.builder import AgentServerBuildConfig

        build_config = AgentServerBuildConfig(
            base_image=self.base_image,
            variant=self.build_variant,
            target=self.build_target,
            registry_prefix=self.registry_prefix,
        )
        logger.info(f"Build config: {build_config.version}, tags: {build_config.tags}")
        self._build_config = build_config
        object.__setattr__(self, "build_context_path", str(build_config.build_context))
        object.__setattr__(self, "build_tags", build_config.tags)

    def build_image_via_api(
        self,
        path: str,
        tags: list[str],
        platform: str | None = None,
    ) -> str:
        """Build a Docker image using the Runtime API."""
        logger.info(f"Building from {path} with tags: {tags}")

        logger.info("Creating agent-server build context...")
        tar_buffer = create_agent_server_build_context_tarball(sdk_root=path, gzip=True)

        tar_bytes = tar_buffer.getvalue()
        base64_encoded_tar = base64.b64encode(tar_bytes).decode("utf-8")
        logger.info(
            f"Tarball size: {len(tar_bytes) / 1024:.1f} KB "
            f"({len(base64_encoded_tar) / 1024:.1f} KB base64)"
        )

        processed_tags = tags
        if self.registry_prefix:
            processed_tags = [
                f"{self.registry_prefix}/{tag}"
                if not tag.startswith(self.registry_prefix)
                else tag
                for tag in tags
            ]

        # Prepare the build request as multipart/form-data
        # Following OpenHands-v0 pattern exactly - only send context and target_image
        files = [
            ("context", ("context.tar.gz", base64_encoded_tar)),
            ("target_image", (None, processed_tags[0])),
        ]

        # Add additional tags
        for tag in processed_tags[1:]:
            files.append(("tags", (None, tag)))

        try:
            response = self._send_api_request(
                "POST", f"{self.api_url}/build", files=files, timeout=30.0
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Rate limited, retrying in 30s")
                time.sleep(30)
                return self.build_image_via_api(path, tags, platform)
            logger.error(f"Build failed: {e.response.status_code} - {e.response.text}")
            raise RuntimeError(f"Failed to initiate build: {e}") from e

        build_id = response.json()["build_id"]
        logger.info(f"Build ID: {build_id}")
        return self._wait_for_build_completion(build_id)

    def _wait_for_build_completion(self, build_id: str) -> str:
        """Poll the build status endpoint until build completes."""
        start_time = time.time()

        while time.time() - start_time < self.build_timeout:
            try:
                resp = self._send_api_request(
                    "GET",
                    f"{self.api_url}/build_status",
                    params={"build_id": build_id},
                    timeout=30.0,
                )
                status_data = resp.json()
                status = status_data["status"]
                logger.info(f"Build status: {status}")

                if status == "SUCCESS":
                    return str(status_data["image"])

                if status in [
                    "FAILURE",
                    "INTERNAL_ERROR",
                    "TIMEOUT",
                    "CANCELLED",
                    "EXPIRED",
                ]:
                    error = status_data.get("error", f"Build {status}")
                    logger.error(f"Build failed: {error}")
                    try:
                        logs_resp = self._send_api_request(
                            "GET",
                            f"{self.api_url}/build_logs",
                            params={"build_id": build_id},
                            timeout=30.0,
                        )
                        if logs_resp.status_code == 200:
                            logs = logs_resp.text
                            logger.error(f"Build logs:\n{logs}")
                            error = f"{error}\n\nLogs:\n{logs}"
                    except Exception as e:
                        logger.warning(f"Failed to fetch build logs: {e}")
                    raise RuntimeError(error)

                time.sleep(30)
            except httpx.HTTPError:
                time.sleep(30)

        raise RuntimeError(f"Build timeout after {self.build_timeout}s")

    def image_exists(self, image_name: str) -> bool:
        """Check if an image exists in the remote registry."""
        try:
            resp = self._send_api_request(
                "GET",
                f"{self.api_url}/image_exists",
                params={"image": image_name},
                timeout=30.0,
            )
            result = resp.json()
            exists = bool(result["exists"])
            if exists:
                size_mb = result["image"]["image_size_bytes"] / 1024 / 1024
                logger.debug(f"Image {image_name} exists ({size_mb:.1f} MB)")
            return exists
        except httpx.HTTPError as e:
            raise RuntimeError(f"Error checking image: {e}") from e

    def _start_or_attach_to_runtime(self) -> None:
        """Start or attach to an existing runtime."""
        if not self._check_existing_runtime():
            self._start_runtime()

        assert self._runtime_id and self._runtime_url, "Runtime ID/URL not set"
        object.__setattr__(self, "host", self._runtime_url)
        object.__setattr__(self, "api_key", self._session_api_key)
        self._wait_until_runtime_alive()

    def _check_existing_runtime(self) -> bool:
        """Check if there's an existing runtime for this session."""
        try:
            resp = self._send_api_request(
                "GET", f"{self.api_url}/sessions/{self.session_id}"
            )
            data = resp.json()
            status = data.get("status")
            logger.info(f"Runtime status: {status}")

            if status in ("running", "paused"):
                self._parse_runtime_response(resp)
                if status == "paused":
                    try:
                        self._resume_runtime()
                    except Exception as e:
                        logger.error(f"Resume failed: {e}")
                        return False
                return True
            return False
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise

    def _start_runtime(self) -> None:
        """Start a new runtime."""
        # Determine the correct command based on the build target
        command: list[str] = []
        if hasattr(self, "_build_config") and self._build_config:
            if self._build_config.target == "source":
                # For source target, use the venv Python
                command = [
                    "/agent-server/.venv/bin/python",
                    "-m",
                    "openhands.agent_server",
                ]
            else:
                # For binary target, use the standalone binary
                command = ["/usr/local/bin/openhands-agent-server"]

        payload: dict[str, Any] = {
            "image": self.base_image,
            "command": command,
            "working_dir": "/",  # Match Dockerfile WORKDIR
            "environment": {},
            "session_id": self.session_id,
        }

        if self.runtime_class:
            payload["runtime_class"] = self.runtime_class
        if self.resource_factor != 1:
            payload["resource_factor"] = self.resource_factor

        logger.info(f"Starting runtime with {self.base_image}")
        logger.info(f"Payload: {payload}")
        resp = self._send_api_request(
            "POST", f"{self.api_url}/start", json=payload, timeout=self.init_timeout
        )
        self._parse_runtime_response(resp)
        logger.info(f"Runtime {self._runtime_id} at {self._runtime_url}")

    def _resume_runtime(self) -> None:
        """Resume a paused runtime."""
        resp = self._send_api_request(
            "POST",
            f"{self.api_url}/resume",
            json={"runtime_id": self._runtime_id},
            timeout=self.init_timeout,
        )
        self._parse_runtime_response(resp)

    def _parse_runtime_response(self, response: httpx.Response) -> None:
        """Parse the runtime response and extract connection info."""
        data = response.json()
        self._runtime_id = data.get("runtime_id") or data.get("id")
        self._runtime_url = data.get("url")
        self._session_api_key = data.get("session_api_key") or data.get("api_key")
        if not self._runtime_id or not self._runtime_url:
            raise ValueError(f"Invalid runtime response: {data}")

    @tenacity.retry(
        stop=tenacity.stop_after_delay(300),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        retry=tenacity.retry_if_exception_type(RuntimeError),
        reraise=True,
    )
    def _wait_until_runtime_alive(self) -> None:
        """Wait until the runtime becomes alive and responsive."""
        logger.info("Waiting for runtime to become alive...")

        resp = self._send_api_request(
            "GET", f"{self.api_url}/sessions/{self.session_id}"
        )
        data = resp.json()
        pod_status = data.get("pod_status", "").lower()
        logger.info(f"Pod status: {pod_status}")

        restart_count = data.get("restart_count", 0)
        if restart_count > 0:
            restart_reasons = data.get("restart_reasons", [])
            logger.warning(f"Pod restarts: {restart_count}, reasons: {restart_reasons}")

        # Handle different pod states
        if pod_status == "ready":
            # Pod is ready, check health endpoint
            health_url = f"{self._runtime_url}/health"
            logger.info(f"Checking health at: {health_url}")
            try:
                with urlopen(health_url, timeout=5.0) as resp:
                    status = getattr(resp, "status", 200)
                    logger.info(f"Health check response: {status}")
                    if 200 <= status < 300:
                        logger.info("Runtime is alive!")
                        return
                    raise RuntimeError(f"Health check failed with status: {status}")
            except Exception as e:
                logger.warning(f"Health check failed: {e}")
                raise RuntimeError(f"Runtime /health failed: {e}")
        elif pod_status in ("not found", "pending", "running"):
            # Transient states - continue retrying
            logger.debug(f"Runtime not yet ready. Status: {pod_status}")
            raise RuntimeError(f"Runtime not yet ready (status: {pod_status})")
        elif pod_status in ("failed", "unknown", "crashloopbackoff"):
            # Terminal failure states
            pod_logs = data.get("pod_logs", "")
            error_msg = f"Runtime failed (status: {pod_status})"
            if pod_logs:
                logger.error(f"Pod logs: {pod_logs}")
                error_msg += f"\nPod logs: {pod_logs}"
            if pod_status == "crashloopbackoff":
                error_msg = (
                    "Runtime crashed and is restarting (possibly OOM). Try again."
                )
            raise ValueError(error_msg)
        else:
            # Unknown status - log and retry
            logger.warning(f"Unknown pod status: {pod_status}, full response: {data}")
            raise RuntimeError(f"Unknown pod status: {pod_status}")

    def _send_api_request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Send an API request with error handling."""
        response = self._api_session.request(method, url, **kwargs)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            # Log the error response body for debugging
            try:
                error_detail = response.json()
                logger.warning(f"API request failed: {error_detail}")
            except Exception:
                logger.warning(f"API request failed: {response.text}")
            raise
        return response

    def cleanup(self) -> None:
        """Clean up the remote runtime."""
        if not self._runtime_id:
            return

        try:
            if self.keep_alive:
                return

            action = "pause" if self.pause_on_close else "stop"
            logger.info(f"{action.capitalize()}ing runtime {self._runtime_id}")
            self._send_api_request(
                "POST",
                f"{self.api_url}/{action}",
                json={"runtime_id": self._runtime_id},
                timeout=30.0,
            )
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        finally:
            self._runtime_id = None
            self._runtime_url = None
            self._session_api_key = None
            try:
                self._api_session.close()
            except Exception:
                pass

    def __del__(self) -> None:
        self.cleanup()

    def __enter__(self) -> "APIRemoteWorkspace":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.cleanup()
