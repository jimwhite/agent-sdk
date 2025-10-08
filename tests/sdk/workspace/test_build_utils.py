"""Tests for build_utils module."""

import io
import tarfile

import pytest

from openhands.workspace.utils.build_utils import (
    create_build_context_tarball,
    load_dockerignore,
)


@pytest.fixture
def temp_build_context(tmp_path):
    """Create a temporary build context directory with various files."""
    # Create directory structure
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "build").mkdir()
    (tmp_path / ".git").mkdir()
    (tmp_path / "__pycache__").mkdir()

    # Create files
    (tmp_path / "Dockerfile").write_text("FROM python:3.12\n")
    (tmp_path / "README.md").write_text("# Test Project\n")
    (tmp_path / "src" / "main.py").write_text("print('hello')\n")
    (tmp_path / "src" / "util.py").write_text("def util(): pass\n")
    (tmp_path / "tests" / "test_main.py").write_text("def test(): pass\n")
    (tmp_path / "build" / "output.txt").write_text("build output\n")
    (tmp_path / ".git" / "config").write_text("git config\n")
    (tmp_path / "__pycache__" / "main.cpython-312.pyc").write_bytes(b"bytecode")
    (tmp_path / "temp.log").write_text("logs\n")

    return tmp_path


def test_create_tarball_without_dockerignore(temp_build_context):
    """Test creating a tarball without .dockerignore."""
    tarball = create_build_context_tarball(
        temp_build_context, respect_dockerignore=False
    )

    assert isinstance(tarball, io.BytesIO)
    assert tarball.tell() == 0  # Should be at beginning

    # Extract and verify contents
    with tarfile.open(fileobj=tarball, mode="r:gz") as tar:
        members = tar.getmembers()
        names = {m.name for m in members}

        # Should include all files
        assert "Dockerfile" in names
        assert "README.md" in names
        assert "src/main.py" in names
        assert "tests/test_main.py" in names
        assert "build/output.txt" in names


def test_create_tarball_with_dockerignore(temp_build_context):
    """Test creating a tarball with .dockerignore."""
    # Create .dockerignore
    dockerignore_content = """
# Ignore git
.git
.gitignore

# Ignore Python cache
__pycache__
*.pyc
*.pyo

# Ignore build artifacts
build/
*.log
"""
    (temp_build_context / ".dockerignore").write_text(dockerignore_content)

    tarball = create_build_context_tarball(
        temp_build_context, respect_dockerignore=True
    )

    # Extract and verify contents
    with tarfile.open(fileobj=tarball, mode="r:gz") as tar:
        members = tar.getmembers()
        names = {m.name for m in members}

        # Should include these
        assert "Dockerfile" in names
        assert "README.md" in names
        assert "src/main.py" in names
        assert "tests/test_main.py" in names

        # Should exclude these
        assert ".git" not in names
        assert ".git/config" not in names
        assert "__pycache__" not in names
        assert "__pycache__/main.cpython-312.pyc" not in names
        assert "build" not in names or "build/output.txt" not in names
        assert "temp.log" not in names


def test_create_tarball_nonexistent_path():
    """Test creating a tarball with a non-existent path."""
    with pytest.raises(FileNotFoundError):
        create_build_context_tarball("/nonexistent/path")


def test_create_tarball_file_instead_of_directory(tmp_path):
    """Test creating a tarball with a file instead of directory."""
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with pytest.raises(ValueError, match="must be a directory"):
        create_build_context_tarball(file_path)


def test_create_tarball_custom_fileobj(temp_build_context):
    """Test creating a tarball with a custom BytesIO object."""
    custom_buffer = io.BytesIO()
    tarball = create_build_context_tarball(
        temp_build_context, fileobj=custom_buffer, respect_dockerignore=False
    )

    assert tarball is custom_buffer
    assert tarball.tell() == 0  # Should be at beginning


def test_create_tarball_uncompressed(temp_build_context):
    """Test creating an uncompressed tarball."""
    tarball = create_build_context_tarball(
        temp_build_context, gzip=False, respect_dockerignore=False
    )

    # Should be able to open without gzip
    with tarfile.open(fileobj=tarball, mode="r") as tar:
        members = tar.getmembers()
        assert len(members) > 0


def test_load_dockerignore(tmp_path):
    """Test loading .dockerignore patterns."""
    dockerignore_path = tmp_path / ".dockerignore"
    dockerignore_content = """
# Comment line
*.pyc
__pycache__/
.git

# Another comment
*.log
"""
    dockerignore_path.write_text(dockerignore_content)

    patterns = load_dockerignore(dockerignore_path)

    assert "*.pyc" in patterns
    assert "__pycache__/" in patterns
    assert ".git" in patterns
    assert "*.log" in patterns
    # Comments should not be included
    assert not any("comment" in p.lower() for p in patterns)


def test_load_dockerignore_nonexistent():
    """Test loading a non-existent .dockerignore file."""
    patterns = load_dockerignore("/nonexistent/.dockerignore")
    assert patterns == []


def test_dockerignore_with_negation(temp_build_context):
    """Test .dockerignore with negation patterns."""
    # Create .dockerignore with negation
    dockerignore_content = """
*.log
!important.log
"""
    (temp_build_context / ".dockerignore").write_text(dockerignore_content)
    (temp_build_context / "debug.log").write_text("debug")
    (temp_build_context / "important.log").write_text("important")

    tarball = create_build_context_tarball(
        temp_build_context, respect_dockerignore=True
    )

    with tarfile.open(fileobj=tarball, mode="r:gz") as tar:
        names = {m.name for m in tar.getmembers()}

        # important.log should be included due to negation
        assert "important.log" in names
        # debug.log should be excluded
        assert "debug.log" not in names


def test_dockerignore_directory_pattern(temp_build_context):
    """Test .dockerignore with directory patterns."""
    dockerignore_content = """
build/
tests/
"""
    (temp_build_context / ".dockerignore").write_text(dockerignore_content)

    tarball = create_build_context_tarball(
        temp_build_context, respect_dockerignore=True
    )

    with tarfile.open(fileobj=tarball, mode="r:gz") as tar:
        names = {m.name for m in tar.getmembers()}

        # Should include src
        assert "src/main.py" in names

        # Should exclude build and tests directories
        assert "build/output.txt" not in names
        assert "tests/test_main.py" not in names


def test_tarball_size_logging(temp_build_context, caplog):
    """Test that tarball creation logs the size."""
    create_build_context_tarball(temp_build_context)

    # Check that size was logged
    assert any("MB" in record.message for record in caplog.records)
