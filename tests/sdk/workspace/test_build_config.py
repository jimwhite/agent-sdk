"""Tests for build_config module."""

import re

from openhands.workspace.utils.builder import AgentServerBuildConfig


def test_agent_server_build_config():
    """Test AgentServerBuildConfig class."""
    config = AgentServerBuildConfig(
        base_image="nikolaik/python-nodejs:python3.12-nodejs22",
        target="binary",
        registry_prefix="us-central1-docker.pkg.dev/project/repo",
    )

    # Check properties
    assert config.base_image == "nikolaik/python-nodejs:python3.12-nodejs22"
    assert config.target == "binary"
    assert config.registry_prefix == "us-central1-docker.pkg.dev/project/repo"
    assert config.custom_tags == []

    # Check computed properties
    assert config.build_context.exists()
    assert config.dockerfile.exists()
    assert len(config.tags) >= 3
    assert all(tag.startswith(config.registry_prefix) for tag in config.tags)
    
    # Check version is valid semver
    assert isinstance(config.version, str)
    assert re.match(r"^\d+\.\d+\.\d+", config.version)
    
    # Check git info structure
    assert "sha" in config.git_info
    assert "short_sha" in config.git_info
    assert "ref" in config.git_info


def test_agent_server_build_config_to_dict():
    """Test converting config to dictionary."""
    config = AgentServerBuildConfig(
        base_image="python:3.12",
        target="binary",
        registry_prefix=None,
    )

    config_dict = config.to_dict()

    # Should have all expected keys
    assert "base_image" in config_dict
    assert "custom_tags" in config_dict
    assert "target" in config_dict
    assert "registry_prefix" in config_dict
    assert "build_context" in config_dict
    assert "dockerfile" in config_dict
    assert "tags" in config_dict
    assert "version" in config_dict
    assert "git_info" in config_dict

    # Values should match
    assert config_dict["base_image"] == "python:3.12"
    assert config_dict["custom_tags"] == []
    assert config_dict["target"] == "binary"
    assert config_dict["registry_prefix"] is None


def test_agent_server_build_config_with_custom_tags():
    """Test AgentServerBuildConfig with custom tags."""
    custom_tags = ["python", "v1.0"]
    config = AgentServerBuildConfig(
        base_image="python:3.12",
        target="binary",
        registry_prefix="ghcr.io/test/repo",
        custom_tags=custom_tags,
    )

    # Check custom_tags property
    assert config.custom_tags == custom_tags

    # Check that custom tags are included in generated tags
    assert "ghcr.io/test/repo:python" in config.tags
    assert "ghcr.io/test/repo:v1.0" in config.tags

    # Should have 3 hash-based + 2 custom tags
    assert len(config.tags) == 5
