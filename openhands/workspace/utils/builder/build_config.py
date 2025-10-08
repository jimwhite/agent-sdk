"""Build configuration helpers for agent-server images."""

import os
import subprocess
from pathlib import Path

import docker


def get_sdk_root() -> Path:
    """Get the root directory of the SDK."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (
            (parent / "pyproject.toml").exists()
            and (parent / "uv.lock").exists()
            and (parent / "LICENSE").exists()
            and (parent / "openhands").is_dir()
        ):
            return parent
    raise RuntimeError("Could not find SDK root")


def get_agent_server_build_context() -> Path:
    """Get the build context for agent-server (SDK root)."""
    return get_sdk_root()


def get_agent_server_dockerfile() -> Path:
    """Get the path to the agent-server Dockerfile."""
    return get_sdk_root() / "openhands" / "agent_server" / "docker" / "Dockerfile"


def get_sdk_version() -> str:
    """Get the SDK version from package metadata."""
    try:
        from importlib.metadata import version

        return version("openhands-sdk")
    except Exception:
        return "0.0.0"


def get_git_info() -> dict[str, str]:
    """Get git information (SHA, branch)."""
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=get_sdk_root(),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        sha = os.getenv("GITHUB_SHA", "unknown")

    short_sha = sha[:7] if len(sha) >= 7 else sha

    try:
        ref = subprocess.check_output(
            ["git", "symbolic-ref", "-q", "--short", "HEAD"],
            cwd=get_sdk_root(),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        ref = os.getenv("GITHUB_REF", "unknown")

    return {"sha": sha, "short_sha": short_sha, "ref": ref}


def sanitize_branch(branch: str) -> str:
    """Sanitize branch name for use in cache tags.
    
    Args:
        branch: Git branch name (may include refs/heads/ prefix)
        
    Returns:
        Sanitized branch name safe for use in Docker tags
    """
    # Remove refs/heads/ prefix
    sanitized = branch.replace("refs/heads/", "")
    # Replace non-alphanumeric characters with hyphens
    sanitized = "".join(c if c.isalnum() or c in ".-" else "-" for c in sanitized)
    # Convert to lowercase
    return sanitized.lower()


def generate_cache_tags(
    registry_prefix: str,
    variant: str,
    git_ref: str,
) -> tuple[str, list[str]]:
    """Generate cache tags for buildx caching strategy.
    
    Args:
        registry_prefix: Image registry prefix (e.g., 'ghcr.io/all-hands-ai/agent-server')
        variant: Build variant name
        git_ref: Git branch/ref name
        
    Returns:
        Tuple of (primary_cache_ref, fallback_cache_refs) where each ref is a full
        cache reference like 'type=registry,ref=image:tag'
    """
    cache_tag_base = f"buildcache-{variant}"
    
    # Determine primary cache tag based on branch
    if git_ref in ("main", "refs/heads/main"):
        cache_tag = f"{cache_tag_base}-main"
    elif git_ref != "unknown":
        sanitized_ref = sanitize_branch(git_ref)
        cache_tag = f"{cache_tag_base}-{sanitized_ref}"
    else:
        cache_tag = cache_tag_base
    
    # Fallback cache tags (try branch-specific first, then main)
    fallback_tags = (
        [f"{cache_tag_base}-main"] if cache_tag != f"{cache_tag_base}-main" else []
    )
    
    # Format as buildx cache references
    primary_ref = f"type=registry,ref={registry_prefix}:{cache_tag}"
    fallback_refs = [f"type=registry,ref={registry_prefix}:{tag}" for tag in fallback_tags]
    cache_to_ref = f"type=registry,ref={registry_prefix}:{cache_tag},mode=max"
    
    return primary_ref, fallback_refs, cache_to_ref


def generate_agent_server_tags(
    base_image: str = "nikolaik/python-nodejs:python3.12-nodejs22",
    variant: str = "python",
    target: str = "binary",
    registry_prefix: str | None = None,
) -> list[str]:
    """Generate hash-based image tags for agent-server.

    Uses content hashing to prevent duplicate builds - same content = same tags.

    Args:
        base_image: Base Docker image to use
        variant: Build variant (e.g., 'python', 'go')
        target: Build target ('source' or 'binary')
        registry_prefix: Registry prefix (e.g., 'ghcr.io/all-hands-ai/runtime')

    Returns:
        List of image tags in order from most to least specific:
        1. source_tag: vX.Y.Z_lockHash_sourceHash (most specific)
        2. lock_tag: vX.Y.Z_lockHash (medium specific)
        3. versioned_tag: vX.Y.Z_baseImageSlug (least specific)
    """
    from openhands.workspace.utils.hash_utils import generate_image_tags

    sdk_root = get_sdk_root()
    # Add -dev suffix for source builds (development mode)
    suffix = "-dev" if target == "source" else ""
    tags_dict = generate_image_tags(
        base_image=base_image,
        sdk_root=sdk_root,
        source_dir=sdk_root / "openhands",
        version=get_sdk_version(),
        suffix=suffix,
    )
    # Return in order from most to least specific
    tags = [tags_dict["source"], tags_dict["lock"], tags_dict["versioned"]]

    # Use default repo name if no registry_prefix provided
    if registry_prefix:
        return [f"{registry_prefix}:{tag}" for tag in tags]
    else:
        return [f"agent-server:{tag}" for tag in tags]


class AgentServerBuildConfig:
    """Configuration for building agent-server images with hash-based tags."""

    def __init__(
        self,
        base_image: str = "nikolaik/python-nodejs:python3.12-nodejs22",
        variant: str = "python",
        target: str = "binary",
        registry_prefix: str | None = None,
    ):
        self.base_image = base_image
        self.variant = variant
        self.target = target
        self.registry_prefix = registry_prefix
        self.build_context = get_agent_server_build_context()
        self.dockerfile = get_agent_server_dockerfile()
        self.tags = generate_agent_server_tags(
            base_image, variant, target, registry_prefix
        )
        self.version = get_sdk_version()
        self.git_info = get_git_info()

    def to_dict(self) -> dict:
        return {
            "base_image": self.base_image,
            "variant": self.variant,
            "target": self.target,
            "registry_prefix": self.registry_prefix,
            "build_context": str(self.build_context),
            "dockerfile": str(self.dockerfile),
            "tags": self.tags,
            "version": self.version,
            "git_info": self.git_info,
        }

    def build(
        self,
        platform: str | None = None,
        extra_build_args: list[str] | None = None,
        use_local_cache: bool = False,
        docker_client: docker.DockerClient | None = None,
        push: bool = False,
        enable_registry_cache: bool = False,
        builder_name: str | None = None,
    ) -> str:
        """Build the agent-server image using DockerRuntimeBuilder.

        This method uses the hash-based tags and DockerRuntimeBuilder to build
        the agent-server image. It will skip building if the image already exists.

        Args:
            platform: Target platform for the build (e.g., 'linux/amd64').
            extra_build_args: Additional build arguments to pass to Docker.
            use_local_cache: Whether to use local build cache.
            docker_client: Docker client to use. If None, creates a new one.
            push: Whether to push the image to registry (CI mode).
            enable_registry_cache: Whether to use registry-based caching.
            builder_name: Name of buildx builder to create/use for multi-arch builds.

        Returns:
            The full image name with tag (e.g., 'registry/image:tag').
        """
        from openhands.sdk.logger import get_logger
        from openhands.workspace.utils.builder import DockerRuntimeBuilder

        logger = get_logger(__name__)

        # Create builder
        builder = DockerRuntimeBuilder(docker_client)

        # Check if any of the tags already exist (in order from most to least specific)
        # Skip check if pushing (we might want to update the registry)
        if not push:
            for tag in self.tags:
                if builder.image_exists(tag, pull_from_repo=True):
                    logger.info(f"Image {tag} already exists, skipping build")
                    return tag

        # No existing image found, build it
        logger.info(f"Building image with tags: {self.tags}")

        # Prepare build args
        build_args = extra_build_args or []
        build_args.extend(
            [
                f"--build-arg=BASE_IMAGE={self.base_image}",
                f"--build-arg=VARIANT={self.variant}",
                f"--build-arg=VERSION={self.version}",
                f"--target={self.target}",
                f"--file={self.dockerfile}",
            ]
        )

        # Generate registry cache refs if enabled
        registry_cache_from = None
        registry_cache_to = None
        if enable_registry_cache and self.registry_prefix:
            primary_ref, fallback_refs, cache_to_ref = generate_cache_tags(
                registry_prefix=self.registry_prefix,
                variant=self.variant,
                git_ref=self.git_info["ref"],
            )
            registry_cache_from = [primary_ref] + fallback_refs
            registry_cache_to = cache_to_ref
            logger.info(f"Using registry cache: {primary_ref}")
            if fallback_refs:
                logger.info(f"Fallback caches: {', '.join(fallback_refs)}")

        # Build the image
        result_image = builder.build(
            path=str(self.build_context),
            tags=self.tags,
            platform=platform,
            extra_build_args=build_args,
            use_local_cache=use_local_cache,
            push=push,
            registry_cache_from=registry_cache_from,
            registry_cache_to=registry_cache_to,
            builder_name=builder_name,
        )

        logger.info(f"Successfully built image: {result_image}")
        return result_image
