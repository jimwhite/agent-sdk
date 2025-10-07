"""Build configuration helpers for agent-server images."""

import os
import subprocess
from pathlib import Path


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
    from openhands.sdk.workspace.hash_utils import generate_image_tags

    sdk_root = get_sdk_root()
    tags_dict = generate_image_tags(
        base_image=base_image,
        sdk_root=sdk_root,
        source_dir=sdk_root / "openhands",
        version=get_sdk_version(),
    )
    # Return in order from most to least specific
    tags = [tags_dict["source"], tags_dict["lock"], tags_dict["versioned"]]

    return [f"{registry_prefix}/{tag}" for tag in tags] if registry_prefix else tags


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
