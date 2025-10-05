"""Shared utilities for building Docker images and managing build contexts."""

import io
import os
import tarfile
from pathlib import Path

from openhands.sdk.logger import get_logger


logger = get_logger(__name__)


def create_build_context_tarball(
    path: str | Path,
    fileobj: io.BytesIO | None = None,
    gzip: bool = True,
    respect_dockerignore: bool = True,
) -> io.BytesIO:
    """Create a tar archive of a build context directory.

    This function creates a tarball suitable for Docker image builds, optionally
    respecting .dockerignore patterns if present in the build context.

    Args:
        path: Path to the build context directory
        fileobj: Optional BytesIO object to write the archive to. If None, creates new.
        gzip: Whether to gzip compress the archive (default: True)
        respect_dockerignore: Whether to respect .dockerignore file (default: True)

    Returns:
        io.BytesIO: Buffer containing the tar archive

    Raises:
        FileNotFoundError: If the build context path doesn't exist
        ValueError: If the build context path is not a directory

    Example:
        >>> tarball = create_build_context_tarball("./my-docker-context")
        >>> # tarball is ready to be sent to Docker daemon or API
    """
    build_path = Path(path).resolve()

    if not build_path.exists():
        raise FileNotFoundError(f"Build context path does not exist: {path}")

    if not build_path.is_dir():
        raise ValueError(f"Build context path must be a directory: {path}")

    logger.debug(f"Creating build context tarball from: {build_path}")

    # Load .dockerignore patterns if present
    exclude_patterns = []
    dockerignore_path = build_path / ".dockerignore"

    if respect_dockerignore and dockerignore_path.exists():
        logger.debug(f"Loading .dockerignore from: {dockerignore_path}")
        try:
            with open(dockerignore_path) as f:
                exclude_patterns = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]
            logger.debug(f"Loaded {len(exclude_patterns)} exclude patterns")
        except Exception as e:
            logger.warning(f"Failed to read .dockerignore: {e}")
            exclude_patterns = []

    # Create the tar archive
    if fileobj is None:
        fileobj = io.BytesIO()

    mode = "w:gz" if gzip else "w"

    try:
        with tarfile.open(fileobj=fileobj, mode=mode) as tar:
            # Get all files to include
            files_to_add = _get_files_to_include(build_path, exclude_patterns)

            logger.debug(f"Adding {len(files_to_add)} files to tarball")

            for file_path in sorted(files_to_add):
                full_path = build_path / file_path
                arcname = str(file_path)

                try:
                    # Get tar info
                    tarinfo = tar.gettarinfo(str(full_path), arcname=arcname)

                    if tarinfo is None:
                        # This can happen with socket files - skip them
                        logger.debug(f"Skipping special file: {file_path}")
                        continue

                    # Fix for very old or very new timestamps
                    if tarinfo.mtime < 0 or tarinfo.mtime > 8**11 - 1:
                        tarinfo.mtime = int(tarinfo.mtime)

                    # Add file or directory
                    if tarinfo.isfile():
                        with open(full_path, "rb") as f:
                            tar.addfile(tarinfo, f)
                    else:
                        tar.addfile(tarinfo)

                except OSError as e:
                    logger.warning(f"Failed to add file {file_path}: {e}")
                    continue

    except Exception as e:
        logger.error(f"Failed to create tar archive: {e}")
        raise

    # Seek to beginning for reading
    fileobj.seek(0)

    logger.info(
        f"Created build context tarball: {len(fileobj.getvalue()) / 1024 / 1024:.2f} MB"
    )

    return fileobj


def _get_files_to_include(root: Path, exclude_patterns: list[str]) -> list[Path]:
    """Get list of files to include in the build context.

    Args:
        root: Root directory of the build context
        exclude_patterns: List of patterns to exclude (dockerignore format)

    Returns:
        list[Path]: List of relative paths to include
    """
    files_to_include = []

    # Convert exclude patterns to a simpler matcher
    # For now, we'll do basic glob-style matching
    # More sophisticated implementations could use the docker library's PatternMatcher

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)

        # Check if directory should be excluded
        if rel_dir != Path(".") and _should_exclude(rel_dir, exclude_patterns):
            # Clear dirnames to prevent walking into this directory
            dirnames.clear()
            continue

        # Add directory itself (if not root)
        if rel_dir != Path("."):
            files_to_include.append(rel_dir)

        # Add files
        for filename in filenames:
            rel_path = rel_dir / filename if rel_dir != Path(".") else Path(filename)

            # Skip .dockerignore itself
            if str(rel_path) == ".dockerignore":
                continue

            if not _should_exclude(rel_path, exclude_patterns):
                files_to_include.append(rel_path)

        # Filter subdirectories
        dirnames[:] = [
            d
            for d in dirnames
            if not _should_exclude(
                rel_dir / d if rel_dir != Path(".") else Path(d), exclude_patterns
            )
        ]

    return files_to_include


def _should_exclude(path: Path, patterns: list[str]) -> bool:
    """Check if a path should be excluded based on patterns.

    This is a simplified implementation of .dockerignore pattern matching.
    It supports basic glob patterns and negation (!) patterns.

    Args:
        path: Path to check (relative to build context root)
        patterns: List of patterns to match against

    Returns:
        bool: True if path should be excluded, False otherwise
    """
    import fnmatch

    path_str = str(path).replace("\\", "/")  # Normalize to forward slashes
    excluded = False

    for pattern in patterns:
        # Handle negation patterns
        if pattern.startswith("!"):
            negate = True
            pattern = pattern[1:]
        else:
            negate = False

        # Remove leading ./ if present
        if pattern.startswith("./"):
            pattern = pattern[2:]

        # Handle directory patterns (ending with /)
        is_dir_pattern = pattern.endswith("/")
        if is_dir_pattern:
            pattern = pattern.rstrip("/")

        # Match pattern
        matched = False

        # For directory patterns, match the directory and all its contents
        if is_dir_pattern:
            # Check if path starts with the directory pattern
            if path_str == pattern or path_str.startswith(pattern + "/"):
                matched = True
        else:
            # Try exact match
            if fnmatch.fnmatch(path_str, pattern):
                matched = True
            # Try with leading **/ for directory-based patterns
            elif fnmatch.fnmatch(path_str, f"**/{pattern}"):
                matched = True
            # Try matching parent directories
            elif "/" in pattern:
                # For patterns with /, match against full path
                if fnmatch.fnmatch(path_str, pattern):
                    matched = True
                # Also check if pattern matches with wildcard
                elif fnmatch.fnmatch(path_str, f"{pattern}/*"):
                    matched = True
            else:
                # For simple patterns, match against basename
                if fnmatch.fnmatch(Path(path_str).name, pattern):
                    matched = True
                # Also check if it matches any path component
                if any(fnmatch.fnmatch(part, pattern) for part in path_str.split("/")):
                    matched = True

        if matched:
            excluded = not negate

    return excluded


def load_dockerignore(path: str | Path) -> list[str]:
    """Load patterns from a .dockerignore file.

    Args:
        path: Path to the .dockerignore file

    Returns:
        list[str]: List of patterns (empty list if file doesn't exist or can't be read)

    Example:
        >>> patterns = load_dockerignore("./my-context/.dockerignore")
        >>> print(patterns)
        ['__pycache__', '*.pyc', '.git']
    """
    dockerignore_path = Path(path)

    if not dockerignore_path.exists():
        return []

    try:
        with open(dockerignore_path) as f:
            patterns = [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]
        return patterns
    except Exception as e:
        logger.warning(f"Failed to read .dockerignore from {path}: {e}")
        return []
