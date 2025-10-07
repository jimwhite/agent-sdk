"""Hash-based image tag generation utilities.

Ported from OpenHands V0 runtime_build.py to prevent duplicate image builds.

Key concept: Same content = same hash = same tag = reuse existing image
"""

import hashlib
import string
from pathlib import Path
from typing import Any

from openhands.sdk.logger import get_logger


try:
    from dirhash import dirhash

    HAS_DIRHASH = True
except ImportError:
    HAS_DIRHASH = False
    dirhash: Any = None


logger = get_logger(__name__)

_ALPHABET = string.digits + string.ascii_lowercase


def truncate_hash(hash: str) -> str:
    """Convert base16 (hex) hash to base36 and truncate at 16 characters.

    This makes tags shorter while maintaining sufficient uniqueness.
    We can tolerate truncation because we want uniqueness, not cryptographic security.

    Args:
        hash: Hexadecimal hash string (base16)

    Returns:
        Base36 hash string truncated to 16 characters

    Example:
        >>> truncate_hash("a1b2c3d4e5f6")
        '6f5e4d3c2b1a'
    """
    value = int(hash, 16)
    result: list[str] = []
    while value > 0 and len(result) < 16:
        value, remainder = divmod(value, len(_ALPHABET))
        result.append(_ALPHABET[remainder])
    return "".join(result)


def get_hash_for_lock_files(
    base_image: str,
    sdk_root: Path,
    enable_browser: bool = True,
    extra_files: list[str] | None = None,
) -> str:
    """Generate hash of lock files and base image.

    This hash changes only when dependencies or base image change.
    Used for medium-level caching (lock_tag).

    Args:
        base_image: Docker base image (e.g., 'ubuntu:22.04')
        sdk_root: Root directory containing pyproject.toml and uv.lock
        enable_browser: Whether browser support is enabled (affects dependencies)
        extra_files: Additional files to include in hash (e.g., ['requirements.txt'])

    Returns:
        Truncated hash string (16 chars)

    Example:
        >>> get_hash_for_lock_files('ubuntu:22.04', Path('/path/to/sdk'))
        'abc123def456'
    """
    md5 = hashlib.md5()

    # Include base image in hash
    md5.update(base_image.encode())

    # Only include enable_browser in hash when it's False for backward compatibility
    if not enable_browser:
        md5.update(str(enable_browser).encode())

    # Hash lock files
    lock_files = ["pyproject.toml", "uv.lock"]
    if extra_files:
        lock_files.extend(extra_files)

    for file in lock_files:
        file_path = sdk_root / file
        if file_path.exists():
            logger.debug(f"Hashing lock file: {file}")
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5.update(chunk)
        else:
            logger.warning(f"Lock file not found: {file}")

    return truncate_hash(md5.hexdigest())


def get_hash_for_source_files(source_dir: Path) -> str:
    """Generate hash of source code directory.

    This hash changes whenever source code changes.
    Used for fine-grained caching (source_tag).

    Args:
        source_dir: Directory to hash (e.g., openhands/sdk/)

    Returns:
        Truncated hash string (16 chars)

    Raises:
        ImportError: If dirhash library is not installed
        ValueError: If source_dir doesn't exist

    Example:
        >>> get_hash_for_source_files(Path('/path/to/openhands'))
        'xyz789abc123'
    """
    if not HAS_DIRHASH:
        raise ImportError(
            "dirhash library is required for source file hashing. "
            "Install it with: pip install dirhash"
        )

    if not source_dir.exists():
        raise ValueError(f"Source directory does not exist: {source_dir}")

    logger.debug(f"Hashing source directory: {source_dir}")

    dir_hash = dirhash(
        source_dir,
        "md5",
        ignore=[
            ".*/",  # hidden directories
            "__pycache__/",
            "*.pyc",
            "*.md",  # documentation files
        ],
    )

    return truncate_hash(dir_hash)


def get_base_image_slug(base_image: str) -> str:
    """Convert base image name to a URL-safe slug.

    Args:
        base_image: Docker image name
            (e.g., 'nikolaik/python-nodejs:python3.12-nodejs22')

    Returns:
        Slugified image name truncated to 96 chars

    Example:
        >>> get_base_image_slug('ubuntu:22.04')
        'ubuntu_tag_22.04'
        >>> get_base_image_slug('nikolaik/python-nodejs:python3.12-nodejs22')
        'nikolaik_s_python-nodejs_tag_python3.12-nodejs22'
    """
    slug = base_image.replace("/", "_s_").replace(":", "_tag_").lower()
    # Truncate to 96 chars to fit in Docker tag length limit (128 chars total)
    return slug[-96:]


def generate_image_tags(
    base_image: str,
    sdk_root: Path,
    source_dir: Path,
    version: str,
    enable_browser: bool = True,
    extra_lock_files: list[str] | None = None,
    suffix: str = "",
) -> dict[str, str]:
    """Generate all tag levels for hash-based image caching.

    Creates three tag levels from most to least specific:
    - source_tag: Changes with any source or dependency change (finest caching)
    - lock_tag: Changes only with dependency changes (medium caching)
    - versioned_tag: Changes only with version or base image (coarsest caching)

    Args:
        base_image: Docker base image name
        sdk_root: SDK root directory (contains pyproject.toml, uv.lock)
        source_dir: Source code directory to hash
        version: SDK version string
        enable_browser: Whether browser support is enabled
        extra_lock_files: Additional files to include in lock hash
        suffix: Optional suffix to append to all tags
            (e.g., '-dev' for development builds)

    Returns:
        Dictionary with keys 'source', 'lock', 'versioned' mapping to tag strings

    Example:
        >>> tags = generate_image_tags(
        ...     base_image='ubuntu:22.04',
        ...     sdk_root=Path('/sdk'),
        ...     source_dir=Path('/sdk/openhands'),
        ...     version='1.0.0',
        ... )
        >>> tags
        {
            'source': 'v1.0.0_abc123def456_xyz789abc123',
            'lock': 'v1.0.0_abc123def456',
            'versioned': 'v1.0.0_ubuntu_tag_22.04'
        }
    """
    # Generate hash components
    lock_hash = get_hash_for_lock_files(
        base_image, sdk_root, enable_browser, extra_lock_files
    )

    try:
        source_hash = get_hash_for_source_files(source_dir)
    except (ImportError, ValueError) as e:
        logger.warning(f"Could not hash source files: {e}")
        source_hash = "unknown"

    base_slug = get_base_image_slug(base_image)

    # Build tag hierarchy
    tags = {
        "source": f"v{version}_{lock_hash}_{source_hash}{suffix}",  # Most specific
        "lock": f"v{version}_{lock_hash}{suffix}",  # Medium specific
        "versioned": f"v{version}_{base_slug}{suffix}",  # Least specific
    }

    logger.debug(f"Generated tags: {tags}")
    return tags


def check_tag_exists(tag: str, client=None) -> bool:
    """Check if a Docker image with given tag exists locally.

    Args:
        tag: Full image tag (e.g., 'ghcr.io/all-hands-ai/runtime:v1.0.0_abc123')
        client: Optional docker.DockerClient instance (creates new if None)

    Returns:
        True if image exists locally, False otherwise

    Example:
        >>> check_tag_exists('ubuntu:22.04')
        True
        >>> check_tag_exists('nonexistent:tag')
        False
    """
    try:
        import docker
        import docker.errors
    except ImportError:
        logger.warning("docker library not installed, cannot check if tag exists")
        return False

    try:
        if client is None:
            client = docker.from_env()

        client.images.get(tag)
        logger.debug(f"Tag exists locally: {tag}")
        return True
    except docker.errors.ImageNotFound:
        logger.debug(f"Tag not found locally: {tag}")
        return False
    except Exception as e:
        logger.warning(f"Error checking tag existence: {e}")
        return False


def find_existing_tag(tags: dict[str, str], client=None) -> str | None:
    """Find the most specific existing tag from the tag hierarchy.

    Checks tags in order from most to least specific and returns the first one found.
    This enables smart caching: use the most specific cached image available.

    Args:
        tags: Tag dictionary from generate_image_tags()
        client: Optional docker.DockerClient instance

    Returns:
        The most specific existing tag, or None if none exist

    Example:
        >>> tags = {
        ...     'source': 'v1.0.0_abc_xyz',
        ...     'lock': 'v1.0.0_abc',
        ...     'versioned': 'v1.0.0_ubuntu'
        ... }
        >>> find_existing_tag(tags)  # Returns most specific existing tag
        'v1.0.0_abc_xyz'
    """
    # Check in order from most to least specific
    for tag_type in ["source", "lock", "versioned"]:
        tag = tags.get(tag_type)
        if tag and check_tag_exists(tag, client):
            logger.info(f"Found existing {tag_type} tag: {tag}")
            return tag

    logger.info("No existing tags found")
    return None


# Example usage
if __name__ == "__main__":
    from openhands.workspace.builder import get_sdk_root, get_sdk_version

    # Example: Generate tags for current SDK
    try:
        sdk_root = get_sdk_root()
        version = get_sdk_version()
        source_dir = sdk_root / "openhands"

        tags = generate_image_tags(
            base_image="nikolaik/python-nodejs:python3.12-nodejs22",
            sdk_root=sdk_root,
            source_dir=source_dir,
            version=version,
        )

        print("Generated tags:")
        for tag_type, tag in tags.items():
            print(f"  {tag_type:12} = {tag}")

        # Check which tags exist
        print("\nExisting tags:")
        existing = find_existing_tag(tags)
        if existing:
            print(f"  Found: {existing}")
        else:
            print("  None found - need fresh build")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
