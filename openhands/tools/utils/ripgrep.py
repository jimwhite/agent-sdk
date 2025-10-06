"""
Lazy-download ripgrep utility for cross-platform binary management.

This module provides a robust system for ensuring ripgrep is always available
without making the package heavy. It automatically:
- Uses system `rg` if available
- Downloads the correct precompiled binary from GitHub on first use
- Caches it in ~/.cache/openhands/ripgrep/
- Reuses the cached version on subsequent calls
"""

import os
import platform
import shutil
import stat
import tarfile
import urllib.request
import zipfile
from pathlib import Path


# Ripgrep version to download
RIPGREP_VERSION = "14.1.0"

# Platform-specific binary mappings
RIPGREP_BINARIES = {
    ("Linux", "x86_64"): "ripgrep-x86_64-unknown-linux-musl.tar.gz",
    ("Darwin", "x86_64"): "ripgrep-x86_64-apple-darwin.tar.gz",
    ("Darwin", "arm64"): "ripgrep-aarch64-apple-darwin.tar.gz",
    ("Windows", "AMD64"): "ripgrep-x86_64-pc-windows-msvc.zip",
}

# GitHub release URL template
GITHUB_RELEASE_URL = (
    f"https://github.com/BurntSushi/ripgrep/releases/download/{RIPGREP_VERSION}/{{}}"
)


def _get_cache_dir() -> Path:
    """Get the cache directory for ripgrep binaries."""
    if os.name == "nt":  # Windows
        cache_base = Path(os.environ.get("LOCALAPPDATA", "~/.cache"))
    else:  # Unix-like systems
        cache_base = Path(os.environ.get("XDG_CACHE_HOME", "~/.cache"))

    cache_dir = cache_base.expanduser() / "openhands" / "ripgrep"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_platform_info() -> tuple[str, str]:
    """Get normalized platform and architecture information."""
    system = platform.system()
    machine = platform.machine()

    # Normalize architecture names
    if machine in ("aarch64", "arm64"):
        machine = "arm64"
    elif machine in ("x86_64", "AMD64"):
        machine = "x86_64" if system != "Windows" else "AMD64"

    return system, machine


def _find_system_ripgrep() -> str | None:
    """Check if ripgrep is available in the system PATH."""
    return shutil.which("rg")


def _get_binary_filename(system: str) -> str:
    """Get the expected binary filename for the platform."""
    return "rg.exe" if system == "Windows" else "rg"


def _download_and_extract_ripgrep(
    download_url: str, cache_dir: Path, binary_name: str
) -> str:
    """Download and extract ripgrep binary to cache directory."""
    filename = download_url.split("/")[-1]
    download_path = cache_dir / filename
    binary_path = cache_dir / binary_name

    # Download the archive
    print(f"Downloading ripgrep from {download_url}...")
    urllib.request.urlretrieve(download_url, download_path)

    try:
        # Extract the binary
        if filename.endswith(".tar.gz"):
            with tarfile.open(download_path, "r:gz") as tar:
                # Find the rg binary in the archive
                for member in tar.getmembers():
                    if (
                        member.name.endswith(f"/{binary_name}")
                        or member.name == binary_name
                    ):
                        # Extract to cache directory with correct name
                        member.name = binary_name
                        tar.extract(member, cache_dir)
                        break
                else:
                    raise RuntimeError(f"Could not find {binary_name} in archive")

        elif filename.endswith(".zip"):
            with zipfile.ZipFile(download_path, "r") as zip_file:
                # Find the rg binary in the archive
                for name in zip_file.namelist():
                    if name.endswith(f"/{binary_name}") or name.endswith(
                        f"\\{binary_name}"
                    ):
                        # Extract and rename to correct location
                        zip_file.extract(name, cache_dir)
                        extracted_path = cache_dir / name
                        extracted_path.rename(binary_path)
                        break
                else:
                    raise RuntimeError(f"Could not find {binary_name} in archive")

        else:
            raise RuntimeError(f"Unsupported archive format: {filename}")

        # Set executable permissions on Unix-like systems
        if os.name != "nt":
            os.chmod(
                binary_path,
                stat.S_IRWXU
                | stat.S_IRGRP
                | stat.S_IXGRP
                | stat.S_IROTH
                | stat.S_IXOTH,
            )

        print(f"Successfully extracted ripgrep to {binary_path}")
        return str(binary_path)

    finally:
        # Clean up downloaded archive
        if download_path.exists():
            download_path.unlink()


def get_ripgrep_path() -> str:
    """
    Get the path to the ripgrep binary.

    This function implements the lazy-download strategy:
    1. Check if ripgrep is available in system PATH
    2. Check if cached binary exists
    3. Download and cache the appropriate binary for the platform

    Returns:
        str: Absolute path to the ripgrep executable

    Raises:
        RuntimeError: If the platform is not supported or download fails
    """
    # First, try to use system ripgrep
    system_rg = _find_system_ripgrep()
    if system_rg:
        return system_rg

    # Get platform information
    system, machine = _get_platform_info()
    platform_key = (system, machine)

    # Check if platform is supported
    if platform_key not in RIPGREP_BINARIES:
        raise RuntimeError(
            f"Unsupported platform: {system} {machine}. "
            f"Supported platforms: {list(RIPGREP_BINARIES.keys())}"
        )

    # Check if cached binary exists
    cache_dir = _get_cache_dir()
    binary_name = _get_binary_filename(system)
    cached_binary = cache_dir / binary_name

    if cached_binary.exists():
        return str(cached_binary)

    # Download and cache the binary
    binary_filename = RIPGREP_BINARIES[platform_key]
    download_url = GITHUB_RELEASE_URL.format(binary_filename)

    return _download_and_extract_ripgrep(download_url, cache_dir, binary_name)


def clear_cache() -> None:
    """Clear the ripgrep cache directory."""
    cache_dir = _get_cache_dir()
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        print(f"Cleared ripgrep cache: {cache_dir}")


if __name__ == "__main__":
    # Simple CLI for testing
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "clear-cache":
        clear_cache()
    else:
        try:
            rg_path = get_ripgrep_path()
            print(f"Ripgrep path: {rg_path}")
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
