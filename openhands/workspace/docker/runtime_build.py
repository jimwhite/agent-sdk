"""Runtime image build utilities with hash-based tag naming.

Adapted from OpenHands V0 openhands/runtime/utils/runtime_build.py
Refactored to use static Dockerfile with buildx (following V1 pattern from agent_server/docker/build.sh)

Key changes from V0:
- Uses static Dockerfile with ARG-based configuration instead of Jinja2 templates
- Uses docker buildx with cache layers
- Follows build.sh pattern for hash-based tagging
- Maintains V0's hash generation logic for compatibility
"""

import hashlib
import os
import string
import subprocess
from pathlib import Path

from dirhash import dirhash

import openhands
from openhands.sdk import __version__ as oh_version
from openhands.sdk.exceptions import AgentRuntimeBuildError
from openhands.sdk.logger import get_logger


logger = get_logger(__name__)


def get_runtime_image_repo() -> str:
    """Get the runtime image repository name."""
    return os.getenv("OH_RUNTIME_RUNTIME_IMAGE_REPO", "ghcr.io/all-hands-ai/runtime")


def truncate_hash(hash_str: str, length: int = 16) -> str:
    """Truncate a hash string to a shorter base36 representation.

    Converts base16 (hex) to base36 for shorter tags.
    Uses digits (0-9) + lowercase letters (a-z) = 36 characters.
    """
    alphabet = string.digits + string.ascii_lowercase
    value = int(hash_str, 16)

    result = []
    while value > 0 and len(result) < length:
        value, remainder = divmod(value, len(alphabet))
        result.append(alphabet[remainder])

    return "".join(result)


def get_hash_for_lock_files(base_image: str, enable_browser: bool = True) -> str:
    """Generate MD5 hash from lock files and base image.

    Hash includes:
    - Base image name
    - pyproject.toml content
    - poetry.lock or uv.lock content
    - enable_browser flag (if False)

    Returns:
        16-char base36 hash string
    """
    md5 = hashlib.md5()
    md5.update(base_image.encode())

    # Only include enable_browser in hash if it's False (for backward compatibility)
    if not enable_browser:
        md5.update(str(enable_browser).encode())

    # Find openhands package directory
    openhands_source_dir = Path(openhands.__file__).parent

    # Try pyproject.toml
    pyproject_path = Path(openhands_source_dir, "pyproject.toml")
    if not pyproject_path.exists():
        pyproject_path = Path(openhands_source_dir.parent, "pyproject.toml")

    if pyproject_path.exists():
        with open(pyproject_path, "rb") as f:
            while chunk := f.read(4096):
                md5.update(chunk)
    else:
        logger.warning(f"pyproject.toml not found at {pyproject_path}")

    # Try poetry.lock or uv.lock
    lock_path = Path(openhands_source_dir.parent, "poetry.lock")
    if not lock_path.exists():
        lock_path = Path(openhands_source_dir.parent, "uv.lock")

    if lock_path.exists():
        with open(lock_path, "rb") as f:
            while chunk := f.read(4096):
                md5.update(chunk)
    else:
        logger.warning(f"Lock file not found at {lock_path}")

    return truncate_hash(md5.hexdigest())


def get_hash_for_source_files() -> str:
    """Generate hash from openhands source directory.

    Uses dirhash to create consistent hash of entire source tree.
    Ignores: __pycache__, *.pyc, hidden directories

    Returns:
        16-char base36 hash string
    """
    openhands_source_dir = str(Path(openhands.__file__).parent)

    try:
        dir_hash = dirhash(
            openhands_source_dir,
            "md5",
            ignore=["__pycache__", "*.pyc", ".*"],
        )
        return truncate_hash(dir_hash)
    except Exception as e:
        logger.error(f"Failed to hash source directory: {e}")
        # Fallback: use timestamp-based hash
        import time

        return truncate_hash(hashlib.md5(str(time.time()).encode()).hexdigest())


def sanitize_tag(tag: str) -> str:
    """Sanitize image tag for Docker compatibility.

    Replaces:
    - / with _s_ (slash)
    - : with _t_ (tag separator)
    - Makes lowercase
    - Truncates to last 96 chars if too long
    """
    sanitized = tag.replace("/", "_s_").replace(":", "_t_").lower()
    if len(sanitized) > 96:
        sanitized = sanitized[-96:]
    return sanitized


def get_versioned_tag(base_image: str) -> str:
    """Generate versioned tag from OH version and base image.

    Format: oh_v{version}_{sanitized_base_image}
    Example: oh_v1.0.0_python_t_3.12-bookworm
    """
    base_slug = sanitize_tag(base_image)
    return f"oh_v{oh_version}_{base_slug}"


def get_lock_tag(base_image: str, enable_browser: bool = True) -> str:
    """Generate lock tag from OH version and lock file hash.

    Format: oh_v{version}_{lock_hash}
    Example: oh_v1.0.0_a1b2c3d4e5f6g7h8
    """
    lock_hash = get_hash_for_lock_files(base_image, enable_browser)
    return f"oh_v{oh_version}_{lock_hash}"


def get_source_tag(base_image: str, enable_browser: bool = True) -> str:
    """Generate source tag from OH version, lock hash, and source hash.

    Format: oh_v{version}_{lock_hash}_{source_hash}
    Example: oh_v1.0.0_a1b2c3d4e5f6g7h8_i9j0k1l2m3n4o5p6
    """
    lock_hash = get_hash_for_lock_files(base_image, enable_browser)
    source_hash = get_hash_for_source_files()
    return f"oh_v{oh_version}_{lock_hash}_{source_hash}"


def image_exists(image_name: str) -> bool:
    """Check if Docker image exists locally or remotely.

    Args:
        image_name: Full image name with tag (e.g., repo:tag)

    Returns:
        True if image exists, False otherwise
    """
    # Try local first
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image_name],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            logger.debug(f"Image {image_name} exists locally")
            return True
    except Exception as e:
        logger.debug(f"Error checking local image: {e}")

    # Try remote registry
    try:
        result = subprocess.run(
            ["docker", "manifest", "inspect", image_name],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            logger.debug(f"Image {image_name} exists in remote registry")
            return True
    except Exception as e:
        logger.debug(f"Error checking remote image: {e}")

    return False


def build_runtime_image(
    base_image: str,
    platform: str = "linux/amd64",
    enable_browser: bool = True,
    extra_build_args: dict[str, str] | None = None,
    push: bool = False,
    use_cache: bool = True,
) -> str:
    """Build runtime image using hash-based caching.

    Uses 3-tier caching strategy:
    1. Source tag (exact match) - reuse immediately
    2. Lock tag (same dependencies) - fast build (only source changed)
    3. Versioned tag (same base) - medium build (reinstall dependencies)
    4. Scratch build - full build from base image

    Args:
        base_image: Base Docker image (e.g., python:3.12-bookworm)
        platform: Target platform (e.g., linux/amd64)
        enable_browser: Whether to include browser support
        extra_build_args: Additional build arguments
        push: Whether to push to registry
        use_cache: Whether to use build cache

    Returns:
        Full image name with tag
    """
    repo = get_runtime_image_repo()

    # Generate all possible tags
    versioned_tag = get_versioned_tag(base_image)
    lock_tag = get_lock_tag(base_image, enable_browser)
    source_tag = get_source_tag(base_image, enable_browser)

    logger.info(f"Building runtime image from base: {base_image}")
    logger.info(f"  Versioned tag: {versioned_tag}")
    logger.info(f"  Lock tag: {lock_tag}")
    logger.info(f"  Source tag: {source_tag}")

    # Check if source tag already exists (best case - instant reuse)
    full_source_tag = f"{repo}:{source_tag}"
    if use_cache and image_exists(full_source_tag):
        logger.info(f"✓ Image with source tag already exists: {full_source_tag}")
        return full_source_tag

    # Determine which base to build from
    cache_from_images = []
    build_target = "runtime"

    if enable_browser:
        build_target = "with-browser"

    # Check for lock tag (fast path - same dependencies)
    full_lock_tag = f"{repo}:{lock_tag}"
    if use_cache and image_exists(full_lock_tag):
        logger.info(f"✓ Found lock tag: {full_lock_tag} (same dependencies)")
        cache_from_images.append(full_lock_tag)

    # Check for versioned tag (medium path - same base)
    full_versioned_tag = f"{repo}:{versioned_tag}"
    if use_cache and image_exists(full_versioned_tag):
        logger.info(f"✓ Found versioned tag: {full_versioned_tag} (same base)")
        cache_from_images.append(full_versioned_tag)

    # Build the image
    dockerfile_path = Path(__file__).parent / "Dockerfile"
    if not dockerfile_path.exists():
        raise AgentRuntimeBuildError(f"Dockerfile not found at {dockerfile_path}")

    # Prepare build command
    build_args = {
        "BASE_IMAGE": base_image,
        **(extra_build_args or {}),
    }

    # Tags to apply to the built image
    tags_to_apply = [full_source_tag]
    # Also tag with lock and versioned tags if they don't exist
    if not image_exists(full_lock_tag):
        tags_to_apply.append(full_lock_tag)
    if not image_exists(full_versioned_tag):
        tags_to_apply.append(full_versioned_tag)

    cmd = ["docker", "buildx", "build"]

    # Add platform
    cmd.extend(["--platform", platform])

    # Add target
    cmd.extend(["--target", build_target])

    # Add build args
    for key, value in build_args.items():
        cmd.extend(["--build-arg", f"{key}={value}"])

    # Add tags
    for tag in tags_to_apply:
        cmd.extend(["--tag", tag])

    # Add cache sources
    if use_cache:
        for cache_image in cache_from_images:
            cmd.extend(["--cache-from", f"type=registry,ref={cache_image}"])

    # Add cache export for source tag
    if use_cache:
        cmd.extend(["--cache-to", "type=inline"])

    # Push or load
    if push:
        cmd.append("--push")
    else:
        cmd.append("--load")

    # Add dockerfile and context
    cmd.extend(["--file", str(dockerfile_path)])
    cmd.append(str(dockerfile_path.parent))

    logger.info(f"Building with command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,
            text=True,
        )
        logger.info(f"✓ Successfully built runtime image: {full_source_tag}")
        logger.info(f"  All tags: {', '.join(tags_to_apply)}")
        return full_source_tag
    except subprocess.CalledProcessError as e:
        raise AgentRuntimeBuildError(f"Failed to build runtime image: {e}")
