"""Build configuration helpers for agent-server images."""

import os
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field, computed_field

from openhands.workspace.utils.builder.base import RuntimeBuilder


# ============================================================================
# Public Utility Functions (used by other modules)
# ============================================================================

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


# ============================================================================
# Main Build Configuration
# ============================================================================

class AgentServerBuildConfig(BaseModel):
    """Configuration for building agent-server images with hash-based tags."""
    
    base_image: str = "nikolaik/python-nodejs:python3.12-nodejs22"
    target: str = "binary"
    registry_prefix: str | None = None
    custom_tags: list[str] = Field(default_factory=list)
    
    model_config = {"arbitrary_types_allowed": True}
    
    @computed_field
    @property
    def build_context(self) -> Path:
        """Get the build context directory (SDK root)."""
        return get_sdk_root()
    
    @computed_field
    @property
    def dockerfile(self) -> Path:
        """Get the Dockerfile path."""
        return get_sdk_root() / "openhands" / "agent_server" / "docker" / "Dockerfile"
    
    @computed_field
    @property
    def tags(self) -> list[str]:
        """Generate hash-based image tags."""
        return self._generate_tags()
    
    @computed_field
    @property
    def version(self) -> str:
        """Get SDK version."""
        return get_sdk_version()
    
    @computed_field
    @property
    def git_info(self) -> dict[str, str]:
        """Get git information."""
        return get_git_info()
    
    def _generate_tags(self) -> list[str]:
        """Generate hash-based image tags for agent-server.
        
        Uses content hashing to prevent duplicate builds - same content = same tags.
        
        Returns:
            List of image tags in order from most to least specific:
            1. source_tag: vX.Y.Z_lockHash_sourceHash (most specific)
            2. lock_tag: vX.Y.Z_lockHash (medium specific)
            3. versioned_tag: vX.Y.Z_baseImageSlug (least specific)
            4+. custom tags (if provided)
        """
        from openhands.workspace.utils.hash_utils import generate_image_tags
        
        sdk_root = get_sdk_root()
        suffix = "-dev" if self.target == "source" else ""
        tags_dict = generate_image_tags(
            base_image=self.base_image,
            sdk_root=sdk_root,
            source_dir=sdk_root / "openhands",
            version=self.version,
            suffix=suffix,
        )
        
        tags = [tags_dict["source"], tags_dict["lock"], tags_dict["versioned"]]
        
        if self.custom_tags:
            tags.extend(self.custom_tags)
        
        if self.registry_prefix:
            return [f"{self.registry_prefix}:{tag}" for tag in tags]
        else:
            return [f"agent-server:{tag}" for tag in tags]
    
    def get_build_args(self) -> list[str]:
        """Get the Docker build arguments for this configuration."""
        return [
            f"--build-arg=BASE_IMAGE={self.base_image}",
            f"--build-arg=VERSION={self.version}",
            f"--target={self.target}",
            f"--file={self.dockerfile}",
        ]
    
    def generate_cache_tags(self) -> tuple[str, list[str], str]:
        """Generate cache tags for buildx caching strategy.
        
        Returns:
            Tuple of (primary_cache_ref, fallback_cache_refs, cache_to_ref) where each ref
            is a full cache reference like 'type=registry,ref=image:tag'
        """
        if not self.registry_prefix:
            raise ValueError("registry_prefix required for cache tags")
        
        from openhands.workspace.utils.hash_utils import get_base_image_slug
        
        base_slug = get_base_image_slug(self.base_image)
        cache_tag_base = f"buildcache-{base_slug}"
        git_ref = self.git_info["ref"]
        
        # Determine primary cache tag based on branch
        if git_ref in ("main", "refs/heads/main"):
            cache_tag = f"{cache_tag_base}-main"
        elif git_ref != "unknown":
            sanitized_ref = self._sanitize_branch(git_ref)
            cache_tag = f"{cache_tag_base}-{sanitized_ref}"
        else:
            cache_tag = cache_tag_base
        
        # Fallback cache tags
        fallback_tags = (
            [f"{cache_tag_base}-main"] if cache_tag != f"{cache_tag_base}-main" else []
        )
        
        # Format as buildx cache references
        primary_ref = f"type=registry,ref={self.registry_prefix}:{cache_tag}"
        fallback_refs = [
            f"type=registry,ref={self.registry_prefix}:{tag}" for tag in fallback_tags
        ]
        cache_to_ref = f"type=registry,ref={self.registry_prefix}:{cache_tag},mode=max"
        
        return primary_ref, fallback_refs, cache_to_ref
    
    @staticmethod
    def _sanitize_branch(branch: str) -> str:
        """Sanitize branch name for use in cache tags."""
        sanitized = branch.replace("refs/heads/", "")
        sanitized = "".join(c if c.isalnum() or c in ".-" else "-" for c in sanitized)
        return sanitized.lower()
    
    def build(
        self,
        builder: RuntimeBuilder,
        platform: str | None = None,
        extra_build_args: list[str] | None = None,
        use_local_cache: bool = False,
        push: bool = False,
        enable_registry_cache: bool = False,
        builder_name: str | None = None,
    ) -> str:
        """Build agent-server image using this configuration.
        
        Args:
            builder: RuntimeBuilder instance to use for building
            platform: Target platform for the build (e.g., 'linux/amd64')
            extra_build_args: Additional build arguments to pass to Docker
            use_local_cache: Whether to use local build cache
            push: Whether to push the image to registry (CI mode)
            enable_registry_cache: Whether to use registry-based caching
            builder_name: Name of buildx builder to create/use for multi-arch builds
            
        Returns:
            The full image name with tag (e.g., 'registry/image:tag')
        """
        from openhands.sdk.logger import get_logger
        
        logger = get_logger(__name__)
        
        # Check if any of the tags already exist (skip if pushing)
        if not push:
            for tag in self.tags:
                if builder.image_exists(tag, pull_from_repo=True):
                    logger.info(f"Image {tag} already exists, skipping build")
                    return tag
        
        logger.info(f"Building image with tags: {self.tags}")
        
        # Prepare build args
        build_args = self.get_build_args()
        if extra_build_args:
            build_args.extend(extra_build_args)
        
        # Generate registry cache refs if enabled
        registry_cache_from = None
        registry_cache_to = None
        if enable_registry_cache and self.registry_prefix:
            primary_ref, fallback_refs, cache_to_ref = self.generate_cache_tags()
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
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "base_image": self.base_image,
            "target": self.target,
            "registry_prefix": self.registry_prefix,
            "custom_tags": self.custom_tags,
            "build_context": str(self.build_context),
            "dockerfile": str(self.dockerfile),
            "tags": self.tags,
            "version": self.version,
            "git_info": self.git_info,
        }



