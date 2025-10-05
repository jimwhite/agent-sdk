"""Build configuration helpers for agent-server images.

This module extracts configuration from openhands/agent_server/docker/build.sh
to allow programmatic building of agent-server images.
"""

import os
import subprocess
from pathlib import Path


def get_sdk_root() -> Path:
    """Get the root directory of the SDK."""
    # Start from this file and go up to find the root with all required files
    # We need to find the directory that contains:
    # - pyproject.toml
    # - uv.lock
    # - openhands/ directory
    # - LICENSE
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (
            (parent / "pyproject.toml").exists()
            and (parent / "uv.lock").exists()
            and (parent / "LICENSE").exists()
            and (parent / "openhands").is_dir()
        ):
            return parent
    raise RuntimeError(
        "Could not find SDK root (pyproject.toml, uv.lock, "
        "LICENSE, and openhands/ not found)"
    )


def get_agent_server_build_context() -> Path:
    """Get the build context for agent-server (SDK root).

    The agent-server Dockerfile expects to be built from the SDK root,
    which contains:
    - pyproject.toml
    - uv.lock
    - README.md
    - LICENSE
    - openhands/

    Returns:
        Path to the SDK root directory
    """
    return get_sdk_root()


def get_agent_server_dockerfile() -> Path:
    """Get the path to the agent-server Dockerfile.

    Returns:
        Path to openhands/agent_server/docker/Dockerfile
    """
    return get_sdk_root() / "openhands" / "agent_server" / "docker" / "Dockerfile"


def get_sdk_version() -> str:
    """Get the SDK version from package metadata.

    Returns:
        Version string (e.g., "0.1.0")
    """
    try:
        from importlib.metadata import version

        return version("openhands-sdk")
    except Exception:
        return "0.0.0"


def get_git_info() -> dict[str, str]:
    """Get git information (SHA, branch).

    Returns:
        Dictionary with 'sha', 'short_sha', 'ref' keys
    """
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

    return {
        "sha": sha,
        "short_sha": short_sha,
        "ref": ref,
    }


def generate_agent_server_tags(
    base_image: str = "nikolaik/python-nodejs:python3.12-nodejs22",
    variant: str = "python",
    target: str = "binary",
    registry_prefix: str | None = None,
) -> list[str]:
    """Generate image tags for agent-server following build.sh convention.

    Args:
        base_image: Base image to build from (e.g.,
            "nikolaik/python-nodejs:python3.12-nodejs22")
        variant: Variant name: "python", "java", or "golang"
        target: Build target: "binary" (prod) or "source" (dev)
        registry_prefix: Optional registry prefix to prepend

    Returns:
        List of image tags to apply
    """
    git_info = get_git_info()
    version = get_sdk_version()

    # Create base slug (matches build.sh format)
    base_slug = base_image.replace("/", "_s_").replace(":", "_tag_")
    versioned_tag = f"v{version}_{base_slug}_{variant}"

    # Build tags
    tags = []
    short_sha = git_info["short_sha"]
    ref = git_info["ref"]

    if target == "source":
        # Dev tags
        tags = [
            f"{short_sha}-{variant}-dev",
            f"{versioned_tag}-dev",
        ]
        if ref in ["main", "refs/heads/main"]:
            tags.append(f"latest-{variant}-dev")
    else:
        # Prod tags
        tags = [
            f"{short_sha}-{variant}",
            f"{versioned_tag}",
        ]
        if ref in ["main", "refs/heads/main"]:
            tags.append(f"latest-{variant}")

    # Prepend registry prefix if provided
    if registry_prefix:
        tags = [f"{registry_prefix}/{tag}" for tag in tags]

    return tags


class AgentServerBuildConfig:
    """Configuration for building agent-server images.

    This class encapsulates all the configuration needed to build
    an agent-server image following the patterns from build.sh.

    Example (New Simplified API - Recommended):
        # Just use build_agent_server=True - everything is automatic!
        workspace = APIRemoteWorkspace(
            api_url="https://runtime.eval.all-hands.dev",
            runtime_api_key="...",
            base_image="nikolaik/python-nodejs:python3.12-nodejs22",
            working_dir="/workspace",
            build_agent_server=True,  # Auto-configures everything!
            build_variant="python",
            build_target="binary",
            registry_prefix="us-central1-docker.pkg.dev/project/repo",
        )

    Example (Advanced - Manual Configuration):
        # For advanced use cases, you can manually configure:
        config = AgentServerBuildConfig(
            base_image="nikolaik/python-nodejs:python3.12-nodejs22",
            variant="python",
            target="binary",
            registry_prefix="us-central1-docker.pkg.dev/project/repo",
        )

        workspace = APIRemoteWorkspace(
            api_url="...",
            runtime_api_key="...",
            base_image=config.tags[0],
            working_dir="/workspace",
            build_context_path=str(config.build_context),
            build_tags=config.tags,
            registry_prefix=config.registry_prefix,
        )
    """

    def __init__(
        self,
        base_image: str = "nikolaik/python-nodejs:python3.12-nodejs22",
        variant: str = "python",
        target: str = "binary",
        registry_prefix: str | None = None,
    ):
        """Initialize build configuration.

        Args:
            base_image: Base image for the Dockerfile
            variant: Variant name: "python", "java", or "golang"
            target: Build target: "binary" (prod) or "source" (dev)
            registry_prefix: Optional registry prefix for image tags
        """
        self.base_image = base_image
        self.variant = variant
        self.target = target
        self.registry_prefix = registry_prefix

        # Computed properties
        self.build_context = get_agent_server_build_context()
        self.dockerfile = get_agent_server_dockerfile()
        self.tags = generate_agent_server_tags(
            base_image=base_image,
            variant=variant,
            target=target,
            registry_prefix=registry_prefix,
        )
        self.version = get_sdk_version()
        self.git_info = get_git_info()

    def to_dict(self) -> dict:
        """Convert configuration to a dictionary.

        Returns:
            Dictionary with all configuration values
        """
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
