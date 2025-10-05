"""API-based remote workspace implementation using runtime API."""

import base64
import json
import time
import urllib.error
from typing import Any
from urllib.request import urlopen

import httpx
import tenacity
from pydantic import Field, PrivateAttr

from openhands.sdk.logger import get_logger
from openhands.sdk.workspace.build_config import AgentServerBuildConfig
from openhands.sdk.workspace.build_utils import create_build_context_tarball
from openhands.sdk.workspace.remote.base import RemoteWorkspace


logger = get_logger(__name__)


class APIRemoteWorkspace(RemoteWorkspace):
    """Remote workspace that provisions a runtime via the OpenHands runtime API.

    This workspace uses the OpenHands remote runtime API to start an agent server
    in a remote sandboxed environment. It handles runtime provisioning, lifecycle
    management, and provides remote workspace operations through the runtime's API.

    Example (with automatic agent-server build):
        workspace = APIRemoteWorkspace(
            api_url="https://runtime.eval.all-hands.dev",
            runtime_api_key="your-api-key",
            base_image="nikolaik/python-nodejs:python3.12-nodejs22",
            build_agent_server=True,  # Auto-builds agent-server image!
            registry_prefix="gcr.io/project/repo",
        )
        result = workspace.execute_command("ls -la")

    Example (using pre-built image):
        workspace = APIRemoteWorkspace(
            api_url="https://runtime.eval.all-hands.dev",
            runtime_api_key="your-api-key",
            base_image="nikolaik/python-nodejs:python3.12-nodejs22",
        )
        result = workspace.execute_command("ls -la")
    """

    # Core required fields
    api_url: str = Field(description="Base URL of the remote runtime API")
    runtime_api_key: str = Field(description="API key for runtime API authentication")
    base_image: str = Field(description="Base container image to use")

    # Optional runtime configuration
    session_id: str | None = Field(
        default=None, description="Session ID for the runtime. Auto-generated if None."
    )
    resource_factor: int = Field(
        default=1, description="Resource scaling factor (1, 2, 4, or 8)"
    )
    runtime_class: str | None = Field(
        default=None, description="Runtime class (e.g., 'sysbox', 'gvisor')"
    )

    # Timeouts
    init_timeout: float = Field(
        default=300.0, description="Timeout for runtime initialization in seconds"
    )
    api_timeout: float = Field(
        default=60.0, description="Timeout for API requests in seconds"
    )
    build_timeout: float = Field(
        default=1800.0,
        description="Timeout for image build in seconds (default: 30 minutes)",
    )

    # Lifecycle management
    keep_alive: bool = Field(
        default=False, description="Keep runtime alive after workspace is destroyed"
    )
    pause_on_close: bool = Field(
        default=False, description="Pause runtime instead of stopping it on cleanup"
    )

    # Build configuration (simplified API - use build_agent_server=True)
    build_agent_server: bool = Field(
        default=False,
        description="If True, automatically build agent-server image "
        "using Runtime API. "
        "This uses openhands/agent_server/docker/Dockerfile from the SDK.",
    )
    registry_prefix: str | None = Field(
        default=None,
        description="Registry prefix for built images (e.g., 'gcr.io/project/repo'). "
        "Required when build_agent_server=True.",
    )
    build_variant: str = Field(
        default="python",
        description="Agent-server variant: 'python', 'java', or 'golang' "
        "(only used with build_agent_server=True)",
    )
    build_target: str = Field(
        default="binary",
        description="Build target: 'binary' (prod) or 'source' (dev) "
        "(only used with build_agent_server=True)",
    )

    # Advanced: Manual build configuration
    # (auto-configured when build_agent_server=True)
    # Only use these if you need full manual control over the build process.
    # When build_agent_server=True, these are automatically
    # configured and should not be provided.
    build_context_path: str | None = Field(
        default=None,
        repr=False,
        description="[Advanced] Path to build context directory. "
        "Auto-configured when build_agent_server=True. "
        "For most users, use build_agent_server=True instead of setting this directly.",
    )
    build_tags: list[str] | None = Field(
        default=None,
        repr=False,
        description="[Advanced] Tags for built image. Auto-configured "
        "when build_agent_server=True. "
        "For most users, use build_agent_server=True instead of setting this directly.",
    )

    # Auto-set during runtime initialization (do not provide)
    host: str = Field(
        default="",
        exclude=True,
        repr=False,
        description="[Internal] Remote host URL, set "
        "automatically during runtime startup.",
    )

    _runtime_id: str | None = PrivateAttr(default=None)
    _runtime_url: str | None = PrivateAttr(default=None)
    _session_api_key: str | None = PrivateAttr(default=None)
    _api_session: httpx.Client = PrivateAttr()
    _build_config: Any = PrivateAttr(default=None)

    def model_post_init(self, context: Any) -> None:
        """Set up the remote runtime and initialize the workspace."""
        # Generate session ID if not provided
        if self.session_id is None:
            object.__setattr__(self, "session_id", f"agent-server-{int(time.time())}")

        # Validate resource_factor
        if self.resource_factor not in [1, 2, 4, 8]:
            raise ValueError(
                f"resource_factor must be 1, 2, 4, or 8, got {self.resource_factor}"
            )

        # Create API session for runtime management
        self._api_session = httpx.Client(
            headers={"X-API-Key": self.runtime_api_key}, timeout=self.api_timeout
        )

        # Clean up API URL
        object.__setattr__(self, "api_url", self.api_url.rstrip("/"))

        # Auto-configure agent-server build if requested
        if self.build_agent_server:
            logger.info("Auto-configuring agent-server build")
            self._setup_agent_server_build()

        # Build image if build context is provided
        if self.build_context_path:
            logger.info("Building image from context path: %s", self.build_context_path)
            built_image = self.build_image_via_api(
                path=self.build_context_path,
                tags=self.build_tags or [self.base_image],
            )
            logger.info("Successfully built image: %s", built_image)
            # Update base_image to use the newly built image
            object.__setattr__(self, "base_image", built_image)

        # Start or attach to runtime
        try:
            self._start_or_attach_to_runtime()
            logger.info("Remote runtime workspace is ready at %s", self.host)

            # Now initialize the parent RemoteWorkspace with the runtime URL
            super().model_post_init(context)
        except Exception:
            self.cleanup()
            raise

    def _setup_agent_server_build(self) -> None:
        """Auto-configure build settings for agent-server image.

        This method uses AgentServerBuildConfig to automatically set up:
        - build_context_path: SDK root directory
        - build_tags: Generated tags following build.sh convention
        """
        logger.info(
            f"Setting up agent-server build (variant={self.build_variant}, "
            f"target={self.build_target})"
        )

        # Create build configuration
        build_config = AgentServerBuildConfig(
            base_image=self.base_image,
            variant=self.build_variant,
            target=self.build_target,
            registry_prefix=self.registry_prefix,
        )

        logger.info("Agent-server build configuration:")
        logger.info(f"  Version: {build_config.version}")
        logger.info(f"  Build context: {build_config.build_context}")
        logger.info(f"  Dockerfile: {build_config.dockerfile}")
        logger.info(f"  Tags: {build_config.tags}")

        # Store build config for later use
        self._build_config = build_config

        # Set build attributes
        object.__setattr__(self, "build_context_path", str(build_config.build_context))
        object.__setattr__(self, "build_tags", build_config.tags)

    def build_image_via_api(
        self,
        path: str,
        tags: list[str],
        platform: str | None = None,
        respect_dockerignore: bool = True,
    ) -> str:
        """Build a Docker image using the Runtime API's /build endpoint.

        Args:
            path: Path to the build context directory containing Dockerfile
            tags: List of tags to apply to the image (first tag is used as target_image)
            platform: Optional target platform for the build
            respect_dockerignore: Whether to respect .dockerignore file (default: True)

        Returns:
            str: The name:tag of the built image

        Raises:
            RuntimeError: If the build fails or times out
            ValueError: If the build context path doesn't exist or is invalid
        """
        logger.info(f"Building image from path: {path}")
        logger.info(f"Tags: {tags}")
        logger.info(f"Respect .dockerignore: {respect_dockerignore}")

        # Create a tar archive of the build context
        logger.info("Creating tar archive of build context...")
        tar_buffer = create_build_context_tarball(
            path=path,
            gzip=True,
            respect_dockerignore=respect_dockerignore,
        )

        # Encode the tar file as base64 (required by Runtime API)
        tar_bytes = tar_buffer.getvalue()
        base64_encoded_tar = base64.b64encode(tar_bytes).decode("utf-8")
        logger.info(
            f"Build context tarball size: {len(tar_bytes)} bytes, "
            f"base64: {len(base64_encoded_tar)} chars"
        )

        # Apply registry prefix to tags if configured
        processed_tags = tags
        if self.registry_prefix:
            processed_tags = []
            for tag in tags:
                if not tag.startswith(self.registry_prefix):
                    full_tag = f"{self.registry_prefix}/{tag}"
                    logger.info(f"Prepending registry prefix: {tag} -> {full_tag}")
                    processed_tags.append(full_tag)
                else:
                    processed_tags.append(tag)

        # Get build args from config if available
        build_args = {}
        if hasattr(self, "_build_config"):
            build_args["BASE_IMAGE"] = self._build_config.base_image
            build_args["TARGET"] = self._build_config.target

        # Prepare the multipart form data
        files = [
            ("context", (None, base64_encoded_tar)),
            ("target_image", (None, processed_tags[0])),
            # Specify the Dockerfile path relative to the build context
            ("dockerfile", (None, "openhands/agent_server/docker/Dockerfile")),
        ]

        # Add build target if specified
        if hasattr(self, "_build_config"):
            files.append(("target", (None, self._build_config.target)))
            files.append(
                ("build_arg", (None, f"BASE_IMAGE={self._build_config.base_image}"))
            )

        # Add additional tags if present
        for tag in processed_tags[1:]:
            files.append(("tags", (None, tag)))

        # Send the POST request to /build
        logger.info(f"Sending build request to {self.api_url}/build...")
        try:
            response = self._send_api_request(
                "POST",
                f"{self.api_url}/build",
                files=files,
                timeout=30.0,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Build was rate limited. Retrying in 30 seconds.")
                time.sleep(30)
                return self.build_image_via_api(path, tags, platform)
            else:
                # Log response body for debugging
                try:
                    error_detail = e.response.text
                    logger.error(
                        f"Build request failed with status {e.response.status_code}"
                    )
                    logger.error(f"Response: {error_detail}")
                except Exception:
                    pass
                raise RuntimeError(f"Failed to initiate build: {e}") from e

        build_data = response.json()
        build_id = build_data["build_id"]
        logger.info(f"Build initiated with ID: {build_id}")

        # Poll /build_status until the build is complete
        return self._wait_for_build_completion(build_id)

    def _wait_for_build_completion(self, build_id: str) -> str:
        """Poll the build status endpoint until build completes.

        Args:
            build_id: The build ID to poll for

        Returns:
            str: The name:tag of the built image

        Raises:
            RuntimeError: If the build fails or times out
        """
        start_time = time.time()

        while time.time() - start_time < self.build_timeout:
            try:
                status_response = self._send_api_request(
                    "GET",
                    f"{self.api_url}/build_status",
                    params={"build_id": build_id},
                    timeout=30.0,
                )

                if status_response.status_code != 200:
                    logger.error(f"Failed to get build status: {status_response.text}")
                    raise RuntimeError(
                        f"Failed to get build status: {status_response.text}"
                    )

                status_data = status_response.json()
                status = status_data["status"]
                logger.info(f"Build status: {status}")

                if status == "SUCCESS":
                    image = status_data["image"]
                    logger.info(f"Successfully built {image}")
                    return str(image)
                elif status in [
                    "FAILURE",
                    "INTERNAL_ERROR",
                    "TIMEOUT",
                    "CANCELLED",
                    "EXPIRED",
                ]:
                    error_message = status_data.get(
                        "error",
                        f"Build failed with status: {status}. Build ID: {build_id}",
                    )
                    logger.error(f"Build failure details: {error_message}")
                    logger.error(f"Full status response: {status_data}")

                    # Try to fetch build logs for more details
                    try:
                        logs_response = self._send_api_request(
                            "GET",
                            f"{self.api_url}/build_logs",
                            params={"build_id": build_id},
                            timeout=30.0,
                        )
                        if logs_response.status_code == 200:
                            logs = logs_response.text
                            logger.error(f"Build logs:\n{logs}")
                            error_message = f"{error_message}\n\nBuild logs:\n{logs}"
                    except Exception as e:
                        logger.warning(f"Could not fetch build logs: {e}")

                    raise RuntimeError(error_message)

                # Wait before polling again
                time.sleep(30)

            except httpx.HTTPError as e:
                logger.warning(f"Error polling build status: {e}")
                time.sleep(30)
                continue

        raise RuntimeError(
            f"Build timed out after {self.build_timeout} seconds. Build ID: {build_id}"
        )

    def image_exists(self, image_name: str) -> bool:
        """Check if an image exists in the remote registry.

        Args:
            image_name: The name of the image to check (e.g., "repo:tag")

        Returns:
            bool: True if the image exists, False otherwise

        Raises:
            RuntimeError: If the API request fails
        """
        logger.debug(f"Checking if image exists: {image_name}")

        try:
            response = self._send_api_request(
                "GET",
                f"{self.api_url}/image_exists",
                params={"image": image_name},
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error(f"Failed to check image existence: {response.text}")
                raise RuntimeError(f"Failed to check image existence: {response.text}")

            result = response.json()

            if result["exists"]:
                logger.debug(
                    f"Image {image_name} exists. "
                    f"Uploaded at: {result['image']['upload_time']}, "
                    f"Size: {result['image']['image_size_bytes'] / 1024 / 1024:.2f} MB"
                )
            else:
                logger.debug(f"Image {image_name} does not exist.")

            return bool(result["exists"])

        except httpx.HTTPError as e:
            logger.error(f"Error checking image existence: {e}")
            raise RuntimeError(f"Error checking image existence: {e}") from e

    def _start_or_attach_to_runtime(self) -> None:
        """Start or attach to an existing runtime."""
        logger.info("Starting or attaching to remote runtime")

        existing_runtime = self._check_existing_runtime()
        if existing_runtime:
            logger.info(f"Using existing runtime with ID: {self._runtime_id}")
        else:
            logger.info("No existing runtime found, starting a new one")
            self._start_runtime()

        assert self._runtime_id is not None, "Runtime ID is not set"
        assert self._runtime_url is not None, "Runtime URL is not set"

        # Set host and api_key for RemoteWorkspace to use
        object.__setattr__(self, "host", self._runtime_url)
        object.__setattr__(self, "api_key", self._session_api_key)

        logger.info("Waiting for runtime to be alive...")
        self._wait_until_runtime_alive()
        logger.info("Runtime is ready.")

    def _check_existing_runtime(self) -> bool:
        """Check if there's an existing runtime for this session."""
        logger.info(f"Checking for existing runtime with session ID: {self.session_id}")

        try:
            response = self._send_api_request(
                "GET", f"{self.api_url}/sessions/{self.session_id}"
            )
            data = response.json()
            status = data.get("status")
            logger.info(f"Found runtime with status: {status}")

            if status in ("running", "paused"):
                self._parse_runtime_response(response)

                if status == "running":
                    logger.info("Found existing runtime in running state")
                    return True
                elif status == "paused":
                    logger.info(
                        "Found existing runtime in paused state, attempting to resume"
                    )
                    try:
                        self._resume_runtime()
                        logger.info("Successfully resumed paused runtime")
                        return True
                    except Exception as e:
                        logger.error(f"Failed to resume paused runtime: {e}")
                        return False
            elif status == "stopped":
                logger.info("Found existing runtime, but it is stopped")
                return False
            else:
                logger.error(f"Invalid response from runtime API: {data}")
                return False

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.info(
                    f"No existing runtime found for session ID: {self.session_id}"
                )
                return False
            logger.error(f"Error while looking for remote runtime: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from runtime API: {e}")
            raise

        return False

    def _start_runtime(self) -> None:
        """Start a new runtime."""
        logger.info(f"Starting new runtime with image: {self.base_image}")

        payload: dict[str, Any] = {
            "image": self.base_image,
            "command": [
                "/openhands/micromamba/bin/python",
                "-m",
                "openhands.agent_server.server",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ],
            "working_dir": "/openhands/code/",
            "environment": {},
            "session_id": self.session_id,
        }

        if self.runtime_class:
            payload["runtime_class"] = self.runtime_class

        if self.resource_factor != 1:
            payload["resource_factor"] = self.resource_factor

        logger.info(f"Creating runtime with payload: {payload}")

        try:
            response = self._send_api_request(
                "POST",
                f"{self.api_url}/start",
                json=payload,
                timeout=self.init_timeout,
            )

            logger.info(f"Runtime created with status {response.status_code}")
            self._parse_runtime_response(response)
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create runtime: {e}")
            if hasattr(e, "response") and hasattr(e.response, "text"):
                logger.error(f"Error response: {e.response.text}")
            raise

        logger.info(
            f"Runtime started with ID {self._runtime_id} at {self._runtime_url}"
        )

    def _resume_runtime(self) -> None:
        """Resume a paused runtime."""
        logger.info(f"Resuming runtime with ID: {self._runtime_id}")

        response = self._send_api_request(
            "POST",
            f"{self.api_url}/resume",
            json={"runtime_id": self._runtime_id},
            timeout=self.init_timeout,
        )

        logger.info(f"Runtime resumed with status {response.status_code}")
        self._parse_runtime_response(response)

        logger.info(
            f"Runtime resumed with ID {self._runtime_id} at {self._runtime_url}"
        )

    def _parse_runtime_response(self, response: httpx.Response) -> None:
        """Parse the runtime response and extract connection info."""
        data = response.json()
        # Runtime API returns 'runtime_id' not 'id'
        self._runtime_id = data.get("runtime_id") or data.get("id")
        self._runtime_url = data.get("url")
        # Runtime API returns 'session_api_key' not 'api_key'
        self._session_api_key = data.get("session_api_key") or data.get("api_key")

        if not self._runtime_id or not self._runtime_url:
            raise ValueError(f"Invalid runtime response: {data}")

    @tenacity.retry(
        stop=tenacity.stop_after_delay(300),  # Increased to 5 minutes for image pull
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        retry=tenacity.retry_if_exception_type(Exception),
        reraise=True,
    )
    def _wait_until_runtime_alive(self) -> None:
        """Wait until the runtime becomes alive and responsive."""
        assert self._runtime_url is not None, "Runtime URL is not set"

        # First check pod status via API
        try:
            response = self._send_api_request(
                "GET", f"{self.api_url}/sessions/{self.session_id}"
            )
            data = response.json()
            pod_status = data.get("pod_status")
            restart_count = data.get("restart_count", 0)

            logger.debug(f"Pod status: {pod_status}, Restart count: {restart_count}")

            if restart_count > 0:
                logger.warning(f"Pod has restarted {restart_count} times")
                restart_reasons = data.get("restart_reasons", [])
                if restart_reasons:
                    logger.warning(f"Restart reasons: {restart_reasons}")

            if pod_status != "Running":
                logger.debug(f"Pod not yet running (status: {pod_status})")
                raise RuntimeError(f"Pod not yet running: {pod_status}")
        except Exception as e:
            logger.debug(f"Could not check pod status: {e}")
            # Continue to health check anyway

        # Then check health endpoint
        health_url = f"{self._runtime_url}/health"
        logger.debug(f"Checking runtime health at {health_url}")

        try:
            with urlopen(health_url, timeout=5.0) as resp:
                status = getattr(resp, "status", 200)
                if 200 <= status < 300:
                    logger.info("Runtime is alive and healthy")
                    return
                logger.warning(f"Runtime health check returned status {status}")
                raise RuntimeError(f"Runtime health check failed with status {status}")
        except urllib.error.HTTPError as e:
            logger.debug(f"Runtime not yet alive (HTTP {e.code}): {e.reason}")
            raise
        except Exception as e:
            logger.debug(f"Runtime not yet alive: {type(e).__name__}: {e}")
            raise

    def _send_api_request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Send an API request with error handling."""
        logger.debug(f"{method} {url}")
        response = self._api_session.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def cleanup(self) -> None:
        """Clean up the remote runtime."""
        if not self._runtime_id:
            return

        try:
            if self.keep_alive:
                logger.info(
                    f"Keeping runtime {self._runtime_id} alive (keep_alive=True)"
                )
                return

            if self.pause_on_close:
                logger.info(f"Pausing runtime {self._runtime_id}")
                self._send_api_request(
                    "POST",
                    f"{self.api_url}/pause",
                    json={"runtime_id": self._runtime_id},
                    timeout=30.0,
                )
            else:
                logger.info(f"Stopping runtime {self._runtime_id}")
                self._send_api_request(
                    "POST",
                    f"{self.api_url}/stop",
                    json={"runtime_id": self._runtime_id},
                    timeout=30.0,
                )
        except Exception as e:
            logger.error(f"Error cleaning up runtime: {e}")
        finally:
            self._runtime_id = None
            self._runtime_url = None
            self._session_api_key = None

            if self._api_session:
                try:
                    self._api_session.close()
                except Exception:
                    pass

    def __del__(self) -> None:
        """Clean up the runtime when the workspace is destroyed."""
        self.cleanup()

    def __enter__(self) -> "APIRemoteWorkspace":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and clean up resources."""
        self.cleanup()
