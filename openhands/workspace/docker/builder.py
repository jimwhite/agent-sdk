"""Docker-based runtime image builder."""

import datetime
import os
import subprocess
import time

import docker
import docker.errors

from openhands.sdk.logger import get_logger
from openhands.workspace.utils.builder.base import RuntimeBuilder
from openhands.workspace.utils.exception import AgentRuntimeBuildError


logger = get_logger(__name__)


class DockerRuntimeBuilder(RuntimeBuilder):
    """Builder for creating Docker runtime images using BuildKit."""

    def __init__(self, docker_client: docker.DockerClient | None = None):
        """Initialize the Docker runtime builder.

        Args:
            docker_client: Docker client instance. If None, creates a new one
                from environment.
        """
        self.docker_client = docker_client or docker.from_env()

        version_info = self.docker_client.version()
        server_version = version_info.get("Version", "").replace("-", ".")
        components = version_info.get("Components", [])
        self.is_podman = components and components[0].get("Name", "").startswith(
            "Podman"
        )

        if (
            tuple(map(int, server_version.split(".")[:2])) < (18, 9)
            and not self.is_podman
        ):
            raise AgentRuntimeBuildError(
                "Docker server version must be >= 18.09 to use BuildKit"
            )

        if self.is_podman and tuple(map(int, server_version.split(".")[:2])) < (4, 9):
            raise AgentRuntimeBuildError("Podman server version must be >= 4.9.0")

    @staticmethod
    def check_buildx(is_podman: bool = False) -> bool:
        """Check if Docker Buildx is available.

        Args:
            is_podman: Whether using Podman instead of Docker.

        Returns:
            True if buildx is available, False otherwise.
        """
        try:
            result = subprocess.run(
                ["docker" if not is_podman else "podman", "buildx", "version"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def build(
        self,
        path: str,
        tags: list[str],
        platform: str | None = None,
        extra_build_args: list[str] | None = None,
        use_local_cache: bool = False,
        push: bool = False,
        registry_cache_from: list[str] | None = None,
        registry_cache_to: str | None = None,
        builder_name: str | None = None,
    ) -> str:
        """Build a Docker image using BuildKit.

        Args:
            path: The path to the Docker build context.
            tags: A list of image tags to apply to the built image.
            platform: The target platform for the build. Defaults to None.
            extra_build_args: Additional arguments to pass to the Docker build command.
            use_local_cache: Whether to use and update the local build cache.
            push: Whether to push the image to registry (CI mode). If True, uses --push
                instead of --load, enabling multi-arch builds.
            registry_cache_from: List of registry cache refs to pull from
                (e.g., ['type=registry,ref=ghcr.io/org/image:cache-main']).
            registry_cache_to: Registry cache ref to push to
                (e.g., 'type=registry,ref=ghcr.io/org/image:cache-main,mode=max').
            builder_name: Name of buildx builder to create/use for multi-arch builds.
                Only used when push=True.

        Returns:
            The name of the built Docker image.

        Raises:
            AgentRuntimeBuildError: If the build process fails.
        """
        # Import version locally to avoid circular import
        from openhands.sdk import __version__ as oh_version

        self.docker_client = docker.from_env()
        version_info = self.docker_client.version()
        server_version = version_info.get("Version", "").split("+")[0].replace("-", ".")
        components = version_info.get("Components", [])
        self.is_podman = components and components[0].get("Name", "").startswith(
            "Podman"
        )

        if tuple(map(int, server_version.split("."))) < (18, 9) and not self.is_podman:
            raise AgentRuntimeBuildError(
                "Docker server version must be >= 18.09 to use BuildKit"
            )

        if self.is_podman and tuple(map(int, server_version.split("."))) < (4, 9):
            raise AgentRuntimeBuildError("Podman server version must be >= 4.9.0")

        if not DockerRuntimeBuilder.check_buildx(self.is_podman):
            logger.warning(
                "Docker buildx not available. Attempting to install Docker binary..."
            )
            self._install_docker_binary()

        target_image_hash_name = tags[0]
        target_image_repo, target_image_source_tag = target_image_hash_name.split(":")
        target_image_tag = tags[1].split(":")[1] if len(tags) > 1 else None

        # Create buildx builder for multi-arch if needed (CI/push mode)
        if push and builder_name:
            logger.debug(f"Creating/using buildx builder: {builder_name}")
            subprocess.run(
                ["docker", "buildx", "create", "--use", "--name", builder_name],
                capture_output=True,
                check=False,
            )
        else:
            # Set default builder for local builds
            subprocess.run(
                ["docker", "buildx", "use", "default"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

        # Build the buildx command
        buildx_cmd = [
            "docker" if not self.is_podman else "podman",
            "buildx",
            "build",
            "--progress=plain",
            f"--build-arg=OPENHANDS_RUNTIME_VERSION={oh_version}",
            f"--build-arg=OPENHANDS_RUNTIME_BUILD_TIME={datetime.datetime.now().isoformat()}",
        ]

        # Add all tags
        for tag in tags:
            buildx_cmd.extend(["--tag", tag])

        # Include the platform argument only if platform is specified
        if platform:
            buildx_cmd.append(f"--platform={platform}")

        # Handle caching
        cache_dir = "/tmp/.buildx-cache"
        
        # Registry cache (for CI or when explicitly provided)
        if registry_cache_from:
            for cache_ref in registry_cache_from:
                buildx_cmd.append(f"--cache-from={cache_ref}")
        
        if registry_cache_to:
            buildx_cmd.append(f"--cache-to={registry_cache_to}")
        
        # Local cache (for local builds)
        if use_local_cache and self._is_cache_usable(cache_dir):
            buildx_cmd.extend(
                [
                    f"--cache-from=type=local,src={cache_dir}",
                    f"--cache-to=type=local,dest={cache_dir},mode=max",
                ]
            )

        # Add extra build args
        if extra_build_args:
            buildx_cmd.extend(extra_build_args)

        # Push vs Load
        if push:
            buildx_cmd.append("--push")
        else:
            buildx_cmd.append("--load")

        buildx_cmd.append(path)  # must be last!

        logger.info(
            f"================ {buildx_cmd[0].upper()} BUILD STARTED ================"
        )
        logger.debug(f"Build command: {' '.join(buildx_cmd)}")

        try:
            process = subprocess.Popen(
                buildx_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )

            output_lines = []
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    line = line.strip()
                    if line:
                        output_lines.append(line)
                        logger.debug(line)

            return_code = process.wait()

            if return_code != 0:
                output_str = "\n".join(output_lines[-50:])
                raise AgentRuntimeBuildError(
                    f"Build failed with return code {return_code}\n"
                    f"Last 50 lines:\n{output_str}"
                )

        except Exception as e:
            logger.error(f"Build failed: {e}")
            raise AgentRuntimeBuildError(f"Build failed: {e}")

        # For push mode, we can't check locally (image is in registry)
        if not push:
            # Check if the image is built successfully locally
            try:
                image = self.docker_client.images.get(target_image_hash_name)
                if image is None:
                    raise AgentRuntimeBuildError(
                        f"Build failed: Image {target_image_hash_name} not found"
                    )
            except docker.errors.ImageNotFound:
                raise AgentRuntimeBuildError(
                    f"Build failed: Image {target_image_hash_name} not found"
                )

        tags_str = (
            f"{target_image_source_tag}, {target_image_tag}"
            if target_image_tag
            else target_image_source_tag
        )
        logger.info(
            f"Image {target_image_repo} with tags [{tags_str}] built successfully"
        )
        return target_image_hash_name

    def image_exists(self, image_name: str, pull_from_repo: bool = True) -> bool:
        """Check if the image exists in the registry or in the local store.

        Args:
            image_name: The Docker image to check (<image repo>:<image tag>)
            pull_from_repo: Whether to pull from the remote repo if not present locally

        Returns:
            Whether the Docker image exists in the registry or in the local store
        """
        if not image_name:
            logger.error(f"Invalid image name: `{image_name}`")
            return False

        try:
            logger.debug(f"Checking if image exists locally: {image_name}")
            self.docker_client.images.get(image_name)
            logger.debug("Image found locally.")
            return True
        except docker.errors.ImageNotFound:
            if not pull_from_repo:
                logger.debug(f"Image {image_name} not found locally")
                return False
            try:
                logger.debug(
                    "Image not found locally. Trying to pull it, please wait..."
                )

                layers: dict[str, dict[str, str | int]] = {}
                previous_layer_count = 0

                if ":" in image_name:
                    image_repo, image_tag = image_name.split(":", 1)
                else:
                    image_repo = image_name
                    image_tag = None

                for line in self.docker_client.api.pull(
                    image_repo, tag=image_tag, stream=True, decode=True
                ):
                    self._output_pull_progress(line, layers, previous_layer_count)
                    previous_layer_count = len(layers)

                logger.debug("Image pulled successfully")
                return True
            except docker.errors.ImageNotFound:
                logger.debug("Could not find image locally or in registry.")
                return False
            except Exception as e:
                ex_msg = str(e)
                if "Not Found" in ex_msg:
                    logger.debug(f"Image {image_name} not found in registry.")
                else:
                    logger.debug(f"Image could not be pulled: {ex_msg}")
                return False

    def _output_pull_progress(
        self,
        current_line: dict,
        layers: dict[str, dict[str, str | int]],
        previous_layer_count: int,
    ) -> None:
        """Output pull progress for image layers.

        Args:
            current_line: Current progress line from Docker API.
            layers: Dictionary tracking layer progress.
            previous_layer_count: Previous count of layers.
        """
        if "id" in current_line and "progressDetail" in current_line:
            layer_id = current_line["id"]
            if layer_id not in layers:
                layers[layer_id] = {"status": "", "progress": "", "last_logged": 0}

            if "status" in current_line:
                layers[layer_id]["status"] = current_line["status"]

            if "progress" in current_line:
                layers[layer_id]["progress"] = current_line["progress"]

            if "progressDetail" in current_line:
                progress_detail = current_line["progressDetail"]
                if "total" in progress_detail and "current" in progress_detail:
                    total = progress_detail["total"]
                    current = progress_detail["current"]
                    percentage = min((current / total) * 100, 100)
                else:
                    percentage = (
                        100 if layers[layer_id]["status"] == "Download complete" else 0
                    )

                # Log progress at 10% intervals
                last_logged = layers[layer_id]["last_logged"]
                if percentage != 0 and (
                    percentage - int(last_logged) >= 10 or percentage == 100  # type: ignore
                ):
                    logger.debug(
                        f"Layer {layer_id}: {layers[layer_id]['progress']} "
                        f"{layers[layer_id]['status']}"
                    )
                    layers[layer_id]["last_logged"] = percentage
        elif "status" in current_line:
            logger.debug(current_line["status"])

    def _install_docker_binary(self) -> None:
        """Install Docker binary if not available (Debian-based systems)."""
        logger.info("No docker binary available, attempting to download and install...")
        commands = [
            "apt-get update",
            "apt-get install -y ca-certificates curl gnupg",
            "install -m 0755 -d /etc/apt/keyrings",
            "curl -fsSL https://download.docker.com/linux/debian/gpg "
            "-o /etc/apt/keyrings/docker.asc",
            "chmod a+r /etc/apt/keyrings/docker.asc",
            'echo "deb [arch=$(dpkg --print-architecture) '
            "signed-by=/etc/apt/keyrings/docker.asc] "
            "https://download.docker.com/linux/debian "
            '$(. /etc/os-release && echo "$VERSION_CODENAME") stable" | '
            "tee /etc/apt/sources.list.d/docker.list > /dev/null",
            "apt-get update",
            "apt-get install -y docker-ce docker-ce-cli containerd.io "
            "docker-buildx-plugin docker-compose-plugin",
        ]
        for cmd in commands:
            try:
                subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL)
            except subprocess.CalledProcessError as e:
                logger.error(f"Image build failed: {e}")
                raise AgentRuntimeBuildError(f"Failed to install Docker: {e}")
        logger.info("Downloaded and installed docker binary")

    def _is_cache_usable(self, cache_dir: str) -> bool:
        """Check if the cache directory is usable (exists and is writable).

        Args:
            cache_dir: The path to the cache directory.

        Returns:
            True if the cache directory is usable, False otherwise.
        """
        if not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir, exist_ok=True)
                logger.debug(f"Created cache directory: {cache_dir}")
            except OSError as e:
                logger.debug(f"Failed to create cache directory {cache_dir}: {e}")
                return False

        if not os.access(cache_dir, os.W_OK):
            logger.warning(
                f"Cache directory {cache_dir} is not writable. "
                "Caches will not be used for Docker builds."
            )
            return False

        self._prune_old_cache_files(cache_dir)

        logger.debug(f"Cache directory {cache_dir} is usable")
        return True

    def _prune_old_cache_files(self, cache_dir: str, max_age_days: int = 7) -> None:
        """Prune cache files older than the specified number of days.

        Args:
            cache_dir: The path to the cache directory.
            max_age_days: The maximum age of cache files in days.
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60

            for root, _, files in os.walk(cache_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > max_age_seconds:
                            os.remove(file_path)
                            logger.debug(f"Removed old cache file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Error processing cache file {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Error during build cache pruning: {e}")
