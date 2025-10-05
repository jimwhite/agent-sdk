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
    """Generate image tags for agent-server following build.sh convention."""
    git_info = get_git_info()
    base_slug = base_image.replace("/", "_s_").replace(":", "_tag_")
    versioned_tag = f"v{get_sdk_version()}_{base_slug}_{variant}"
    short_sha, ref = git_info["short_sha"], git_info["ref"]

    if target == "source":
        tags = [f"{short_sha}-{variant}-dev", f"{versioned_tag}-dev"]
        if ref in ["main", "refs/heads/main"]:
            tags.append(f"latest-{variant}-dev")
    else:
        tags = [f"{short_sha}-{variant}", versioned_tag]
        if ref in ["main", "refs/heads/main"]:
            tags.append(f"latest-{variant}")

    return [f"{registry_prefix}/{tag}" for tag in tags] if registry_prefix else tags


class AgentServerBuildConfig:
    """Configuration for building agent-server images."""

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
