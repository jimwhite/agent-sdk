"""Test configuration and fixtures for server tests."""

import os

import pytest
from fastapi.testclient import TestClient

from openhands.server.main import create_app


@pytest.fixture
def master_key():
    """Test master key."""
    return "test-master-key-12345"


@pytest.fixture
def app(master_key):
    """Create test FastAPI app."""
    # Set master key in environment
    os.environ["OPENHANDS_MASTER_KEY"] = master_key

    # Create app
    app = create_app()

    yield app

    # Clean up
    if "OPENHANDS_MASTER_KEY" in os.environ:
        del os.environ["OPENHANDS_MASTER_KEY"]


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(master_key):
    """Authentication headers for requests."""
    return {"Authorization": f"Bearer {master_key}"}


@pytest.fixture
def sample_agent_config():
    """Sample agent configuration for testing."""
    return {
        "llm_config": {
            "model": "gpt-4",
            "api_key": "test-key",
            "base_url": "https://api.openai.com/v1",
        },
        "tools": ["bash", "file_editor"],
        "workdir": "/tmp/test_workspace",
    }
