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
    """Create a tar archive of a build context directory."""
    build_path = Path(path).resolve()
    if not build_path.exists():
        raise FileNotFoundError(f"Build context path does not exist: {path}")
    if not build_path.is_dir():
        raise ValueError(f"Build context path must be a directory: {path}")

    exclude_patterns = []
    if (
        respect_dockerignore
        and (dockerignore_path := build_path / ".dockerignore").exists()
    ):
        try:
            with open(dockerignore_path) as f:
                exclude_patterns = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]
        except Exception as e:
            logger.warning(f"Failed to read .dockerignore: {e}")

    if fileobj is None:
        fileobj = io.BytesIO()

    mode = "w:gz" if gzip else "w"
    with tarfile.open(fileobj=fileobj, mode=mode) as tar:
        for file_path in sorted(_get_files_to_include(build_path, exclude_patterns)):
            try:
                tarinfo = tar.gettarinfo(
                    str(build_path / file_path), arcname=str(file_path)
                )
                if tarinfo is None:
                    continue
                if tarinfo.mtime < 0 or tarinfo.mtime > 8**11 - 1:
                    tarinfo.mtime = int(tarinfo.mtime)
                if tarinfo.isfile():
                    with open(build_path / file_path, "rb") as f:
                        tar.addfile(tarinfo, f)
                else:
                    tar.addfile(tarinfo)
            except OSError as e:
                logger.warning(f"Failed to add {file_path}: {e}")

    fileobj.seek(0)
    size_mb = fileobj.tell() / 1024 / 1024
    logger.info(f"Created tarball: {size_mb:.1f} MB")
    fileobj.seek(0)
    return fileobj


def _get_files_to_include(root: Path, exclude_patterns: list[str]) -> list[Path]:
    """Get list of files to include in the build context."""
    files_to_include = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        if rel_dir != Path(".") and _should_exclude(rel_dir, exclude_patterns):
            dirnames.clear()
            continue
        if rel_dir != Path("."):
            files_to_include.append(rel_dir)
        for filename in filenames:
            rel_path = rel_dir / filename if rel_dir != Path(".") else Path(filename)
            if str(rel_path) != ".dockerignore" and not _should_exclude(
                rel_path, exclude_patterns
            ):
                files_to_include.append(rel_path)
        dirnames[:] = [
            d
            for d in dirnames
            if not _should_exclude(
                rel_dir / d if rel_dir != Path(".") else Path(d), exclude_patterns
            )
        ]
    return files_to_include


def _should_exclude(path: Path, patterns: list[str]) -> bool:
    """Check if a path should be excluded based on .dockerignore patterns."""
    import fnmatch

    path_str = str(path).replace("\\", "/")
    excluded = False

    for pattern in patterns:
        negate = pattern.startswith("!")
        if negate:
            pattern = pattern[1:]
        pattern = pattern[2:] if pattern.startswith("./") else pattern
        is_dir_pattern = pattern.endswith("/")
        if is_dir_pattern:
            pattern = pattern.rstrip("/")

        matched = False
        if is_dir_pattern:
            matched = path_str == pattern or path_str.startswith(pattern + "/")
        else:
            matched = (
                fnmatch.fnmatch(path_str, pattern)
                or fnmatch.fnmatch(path_str, f"**/{pattern}")
                or ("/" in pattern and fnmatch.fnmatch(path_str, f"{pattern}/*"))
                or fnmatch.fnmatch(Path(path_str).name, pattern)
                or any(fnmatch.fnmatch(part, pattern) for part in path_str.split("/"))
            )

        if matched:
            excluded = not negate

    return excluded


def load_dockerignore(path: str | Path) -> list[str]:
    """Load patterns from a .dockerignore file."""
    dockerignore_path = Path(path)
    if not dockerignore_path.exists():
        return []
    try:
        with open(dockerignore_path) as f:
            return [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]
    except Exception as e:
        logger.warning(f"Failed to read .dockerignore: {e}")
        return []
