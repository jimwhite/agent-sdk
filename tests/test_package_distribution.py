"""Test suite to verify package distribution completeness.

This module tests that built tarballs and wheels contain all expected files
from the source codebase, ensuring no files are accidentally excluded during
the build process.
"""

import tarfile
import zipfile
from pathlib import Path

import pytest


# Root directory of the monorepo
REPO_ROOT = Path(__file__).parent.parent

# Package definitions with their source directories and distribution names
PACKAGES = [
    {
        "name": "openhands-sdk",
        "dist_name": "openhands_sdk",
        "source_dir": "openhands-sdk/openhands/sdk",
        "namespace": "openhands/sdk",
    },
    {
        "name": "openhands-tools",
        "dist_name": "openhands_tools",
        "source_dir": "openhands-tools/openhands/tools",
        "namespace": "openhands/tools",
    },
    {
        "name": "openhands-workspace",
        "dist_name": "openhands_workspace",
        "source_dir": "openhands-workspace/openhands/workspace",
        "namespace": "openhands/workspace",
    },
    {
        "name": "openhands-agent-server",
        "dist_name": "openhands_agent_server",
        "source_dir": "openhands-agent-server/openhands/agent_server",
        "namespace": "openhands/agent_server",
    },
]

# File extensions that should be included in the distribution
INCLUDED_EXTENSIONS = {".py", ".typed", ".json", ".yaml", ".yml", ".txt", ".md"}

# Files/directories to exclude from comparison
EXCLUDED_PATTERNS = {
    "__pycache__",
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".egg-info",
    ".pytest_cache",
    ".mypy_cache",
    ".coverage",
    ".git",
    ".DS_Store",
    "dist",
    "build",
}


def should_include_file(file_path: Path) -> bool:
    """Determine if a file should be included in the distribution.

    Args:
        file_path: Path to the file to check

    Returns:
        True if the file should be included in the distribution
    """
    # Check if any parent directory matches excluded patterns
    for part in file_path.parts:
        if part in EXCLUDED_PATTERNS:
            return False

    # Check if file extension is in the included list
    if file_path.suffix in INCLUDED_EXTENSIONS:
        return True

    # Include files without extension if they're in specific locations
    # (e.g., __init__ files without .py extension shouldn't exist, but just in case)
    if file_path.suffix == "" and file_path.name in {"py.typed", "MANIFEST.in"}:
        return True

    return False


def get_source_files(package_info: dict) -> set[str]:
    """Get all distributable files from the package source directory.

    Args:
        package_info: Dictionary containing package metadata

    Returns:
        Set of relative file paths that should be in the distribution
    """
    source_path = REPO_ROOT / package_info["source_dir"]

    if not source_path.exists():
        raise FileNotFoundError(f"Source directory not found: {source_path}")

    files = set()
    # Get the package root (e.g., "openhands-sdk")
    # source_dir is like "openhands-sdk/openhands/sdk"
    # We want to get paths relative to "openhands-sdk"
    # so they include "openhands/sdk/..."
    package_root = REPO_ROOT / package_info["name"]

    for file_path in source_path.rglob("*"):
        if file_path.is_file() and should_include_file(file_path):
            # Get path relative to the package root (e.g., "openhands/sdk/...")
            rel_path = file_path.relative_to(package_root)
            files.add(str(rel_path))

    return files


def get_tarball_files(package_info: dict, version: str = "1.0.0a1") -> set[str]:
    """Get all files from the built tarball.

    Args:
        package_info: Dictionary containing package metadata
        version: Package version string

    Returns:
        Set of relative file paths found in the tarball
    """
    dist_name = package_info["dist_name"]
    tarball_path = (
        REPO_ROOT / package_info["name"] / "dist" / f"{dist_name}-{version}.tar.gz"
    )

    if not tarball_path.exists():
        raise FileNotFoundError(f"Tarball not found: {tarball_path}")

    files = set()
    with tarfile.open(tarball_path, "r:gz") as tar:
        for member in tar.getmembers():
            if member.isfile():
                # Remove the top-level directory from the path
                # e.g., "openhands_sdk-1.0.0a1/openhands/sdk/..." -> "openhands/sdk/..."
                parts = Path(member.name).parts
                if len(parts) > 1:
                    rel_path = Path(*parts[1:])
                    # Only include files in the openhands namespace
                    if str(rel_path).startswith("openhands/"):
                        files.add(str(rel_path))

    return files


def get_wheel_files(package_info: dict, version: str = "1.0.0a1") -> set[str]:
    """Get all files from the built wheel.

    Args:
        package_info: Dictionary containing package metadata
        version: Package version string

    Returns:
        Set of relative file paths found in the wheel
    """
    dist_name = package_info["dist_name"]
    wheel_path = (
        REPO_ROOT
        / package_info["name"]
        / "dist"
        / f"{dist_name}-{version}-py3-none-any.whl"
    )

    if not wheel_path.exists():
        raise FileNotFoundError(f"Wheel not found: {wheel_path}")

    files = set()
    with zipfile.ZipFile(wheel_path, "r") as wheel:
        for file_info in wheel.filelist:
            filename = file_info.filename
            # Only include files in the openhands namespace (not metadata)
            if filename.startswith("openhands/") and not filename.endswith("/"):
                files.add(filename)

    return files


@pytest.mark.parametrize("package_info", PACKAGES, ids=[p["name"] for p in PACKAGES])
def test_tarball_contains_all_source_files(package_info):
    """Test that the tarball contains all expected source files.

    Args:
        package_info: Dictionary containing package metadata
    """
    source_files = get_source_files(package_info)
    tarball_files = get_tarball_files(package_info)

    missing_files = source_files - tarball_files
    extra_files = tarball_files - source_files

    # Generate detailed error message
    errors = []
    if missing_files:
        errors.append(
            f"Missing {len(missing_files)} file(s) from tarball:\n"
            + "\n".join(f"  - {f}" for f in sorted(missing_files)[:10])
        )
        if len(missing_files) > 10:
            errors.append(f"  ... and {len(missing_files) - 10} more")

    # Extra files are not necessarily an error, but we should warn about them
    if extra_files:
        extra_msg = (
            f"Found {len(extra_files)} extra file(s) in tarball "
            "(this may be expected for generated files):\n"
            + "\n".join(f"  - {f}" for f in sorted(extra_files)[:5])
        )
        if len(extra_files) > 5:
            extra_msg += f"\n  ... and {len(extra_files) - 5} more"
        # Just print as warning, don't fail the test
        print(f"\nWARNING: {extra_msg}")

    assert not missing_files, "\n".join(errors)


@pytest.mark.parametrize("package_info", PACKAGES, ids=[p["name"] for p in PACKAGES])
def test_wheel_contains_all_source_files(package_info):
    """Test that the wheel contains all expected source files.

    Args:
        package_info: Dictionary containing package metadata
    """
    source_files = get_source_files(package_info)
    wheel_files = get_wheel_files(package_info)

    missing_files = source_files - wheel_files
    extra_files = wheel_files - source_files

    # Generate detailed error message
    errors = []
    if missing_files:
        errors.append(
            f"Missing {len(missing_files)} file(s) from wheel:\n"
            + "\n".join(f"  - {f}" for f in sorted(missing_files)[:10])
        )
        if len(missing_files) > 10:
            errors.append(f"  ... and {len(missing_files) - 10} more")

    # Extra files are not necessarily an error
    if extra_files:
        extra_msg = (
            f"Found {len(extra_files)} extra file(s) in wheel "
            "(this may be expected for generated files):\n"
            + "\n".join(f"  - {f}" for f in sorted(extra_files)[:5])
        )
        if len(extra_files) > 5:
            extra_msg += f"\n  ... and {len(extra_files) - 5} more"
        print(f"\nWARNING: {extra_msg}")

    assert not missing_files, "\n".join(errors)


@pytest.mark.parametrize("package_info", PACKAGES, ids=[p["name"] for p in PACKAGES])
def test_tarball_and_wheel_contain_same_files(package_info):
    """Test that tarball and wheel contain the same set of files.

    Args:
        package_info: Dictionary containing package metadata
    """
    tarball_files = get_tarball_files(package_info)
    wheel_files = get_wheel_files(package_info)

    only_in_tarball = tarball_files - wheel_files
    only_in_wheel = wheel_files - tarball_files

    errors = []
    if only_in_tarball:
        errors.append(
            f"Files only in tarball ({len(only_in_tarball)}):\n"
            + "\n".join(f"  - {f}" for f in sorted(only_in_tarball)[:5])
        )

    if only_in_wheel:
        errors.append(
            f"Files only in wheel ({len(only_in_wheel)}):\n"
            + "\n".join(f"  - {f}" for f in sorted(only_in_wheel)[:5])
        )

    assert not only_in_tarball and not only_in_wheel, "\n".join(errors)


def test_all_packages_have_distributions():
    """Test that all packages have been built and have dist files."""
    for package_info in PACKAGES:
        package_name = package_info["name"]
        dist_dir = REPO_ROOT / package_name / "dist"

        assert dist_dir.exists(), f"Distribution directory not found for {package_name}"

        # Check for tarball
        tarballs = list(dist_dir.glob("*.tar.gz"))
        assert tarballs, f"No tarball found for {package_name}"

        # Check for wheel
        wheels = list(dist_dir.glob("*.whl"))
        assert wheels, f"No wheel found for {package_name}"


@pytest.mark.parametrize("package_info", PACKAGES, ids=[p["name"] for p in PACKAGES])
def test_package_has_python_files(package_info):
    """Test that each package contains at least some Python files.

    Args:
        package_info: Dictionary containing package metadata
    """
    source_files = get_source_files(package_info)
    python_files = {f for f in source_files if f.endswith(".py")}

    assert python_files, f"No Python files found in {package_info['name']}"
    assert len(python_files) >= 1, (
        f"Expected at least 1 Python file in {package_info['name']}"
    )


@pytest.mark.parametrize("package_info", PACKAGES, ids=[p["name"] for p in PACKAGES])
def test_package_has_init_file(package_info):
    """Test that each package has an __init__.py file in its root.

    Args:
        package_info: Dictionary containing package metadata
    """
    namespace = package_info["namespace"]
    expected_init = f"{namespace}/__init__.py"

    source_files = get_source_files(package_info)

    assert expected_init in source_files, (
        f"Missing {expected_init} in {package_info['name']}"
    )


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
