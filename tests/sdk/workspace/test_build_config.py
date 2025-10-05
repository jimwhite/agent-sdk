"""Tests for build_config module."""

import re

from openhands.sdk.workspace.build_config import (
    AgentServerBuildConfig,
    generate_agent_server_tags,
    get_agent_server_build_context,
    get_agent_server_dockerfile,
    get_sdk_root,
    get_sdk_version,
)


def test_get_sdk_root():
    """Test getting SDK root directory."""
    root = get_sdk_root()

    # Should exist
    assert root.exists()
    assert root.is_dir()

    # Should contain expected files
    assert (root / "pyproject.toml").exists()
    assert (root / "uv.lock").exists()
    assert (root / "README.md").exists()
    assert (root / "LICENSE").exists()
    assert (root / "openhands").is_dir()


def test_get_agent_server_build_context():
    """Test getting build context (SDK root)."""
    context = get_agent_server_build_context()

    # Build context should be SDK root
    assert context == get_sdk_root()

    # Should contain all required files for Dockerfile
    assert (context / "pyproject.toml").exists()
    assert (context / "uv.lock").exists()
    assert (context / "README.md").exists()
    assert (context / "LICENSE").exists()
    assert (context / "openhands").is_dir()


def test_get_agent_server_dockerfile():
    """Test getting Dockerfile path."""
    dockerfile = get_agent_server_dockerfile()

    # Should exist
    assert dockerfile.exists()
    assert dockerfile.is_file()

    # Should be in expected location
    assert dockerfile.name == "Dockerfile"
    assert dockerfile.parent.name == "docker"
    assert dockerfile.parent.parent.name == "agent_server"

    # Should contain Docker instructions
    content = dockerfile.read_text()
    assert "FROM" in content
    assert "ARG BASE_IMAGE" in content


def test_get_sdk_version():
    """Test getting SDK version."""
    version = get_sdk_version()

    # Should be a valid version string
    assert isinstance(version, str)
    assert re.match(r"^\d+\.\d+\.\d+", version)


def test_generate_agent_server_tags():
    """Test generating image tags."""
    tags = generate_agent_server_tags(
        base_image="nikolaik/python-nodejs:python3.12-nodejs22",
        variant="python",
        target="binary",
        registry_prefix=None,
    )

    # Should have multiple tags
    assert len(tags) >= 2

    # Should contain variant in tags
    assert any("python" in tag for tag in tags)

    # Should have versioned tag
    version = get_sdk_version()
    assert any(f"v{version}" in tag for tag in tags)


def test_generate_agent_server_tags_with_registry_prefix():
    """Test generating tags with registry prefix."""
    prefix = "us-central1-docker.pkg.dev/project/repo"
    tags = generate_agent_server_tags(
        base_image="nikolaik/python-nodejs:python3.12-nodejs22",
        variant="python",
        target="binary",
        registry_prefix=prefix,
    )

    # All tags should start with prefix
    for tag in tags:
        assert tag.startswith(prefix)


def test_generate_agent_server_tags_dev():
    """Test generating dev tags."""
    tags = generate_agent_server_tags(
        base_image="nikolaik/python-nodejs:python3.12-nodejs22",
        variant="python",
        target="source",  # Dev target
        registry_prefix=None,
    )

    # Dev tags should have -dev suffix
    assert all(tag.endswith("-dev") for tag in tags)


def test_agent_server_build_config():
    """Test AgentServerBuildConfig class."""
    config = AgentServerBuildConfig(
        base_image="nikolaik/python-nodejs:python3.12-nodejs22",
        variant="python",
        target="binary",
        registry_prefix="us-central1-docker.pkg.dev/project/repo",
    )

    # Check properties
    assert config.base_image == "nikolaik/python-nodejs:python3.12-nodejs22"
    assert config.variant == "python"
    assert config.target == "binary"
    assert config.registry_prefix == "us-central1-docker.pkg.dev/project/repo"

    # Check computed properties
    assert config.build_context.exists()
    assert config.dockerfile.exists()
    assert len(config.tags) >= 2
    assert all(tag.startswith(config.registry_prefix) for tag in config.tags)
    assert config.version == get_sdk_version()
    assert "sha" in config.git_info
    assert "short_sha" in config.git_info
    assert "ref" in config.git_info


def test_agent_server_build_config_to_dict():
    """Test converting config to dictionary."""
    config = AgentServerBuildConfig(
        base_image="python:3.12",
        variant="python",
        target="binary",
        registry_prefix=None,
    )

    config_dict = config.to_dict()

    # Should have all expected keys
    assert "base_image" in config_dict
    assert "variant" in config_dict
    assert "target" in config_dict
    assert "registry_prefix" in config_dict
    assert "build_context" in config_dict
    assert "dockerfile" in config_dict
    assert "tags" in config_dict
    assert "version" in config_dict
    assert "git_info" in config_dict

    # Values should match
    assert config_dict["base_image"] == "python:3.12"
    assert config_dict["variant"] == "python"
    assert config_dict["target"] == "binary"
    assert config_dict["registry_prefix"] is None
