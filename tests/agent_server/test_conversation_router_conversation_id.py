"""Tests for conversation router with conversation_id functionality."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from openhands.agent_server.api import create_app
from openhands.agent_server.config import Config
from openhands.agent_server.models import ConversationInfo
from openhands.sdk import LLM, Agent
from openhands.sdk.conversation.state import AgentExecutionStatus
from openhands.sdk.security.confirmation_policy import NeverConfirm


@pytest.fixture
def client():
    """Create a test client for the FastAPI app without authentication."""
    config = Config(session_api_keys=[])  # Disable authentication
    return TestClient(create_app(config))


@pytest.fixture
def sample_agent():
    """Create a sample agent for testing."""
    return Agent(
        llm=LLM(model="gpt-4", service_id="test-llm"),
        tools=[],
    )


class TestConversationRouterConversationId:
    """Test cases for conversation router with conversation_id functionality."""

    @patch("openhands.agent_server.conversation_router.conversation_service")
    def test_start_conversation_new_returns_201(
        self, mock_service, client, sample_agent
    ):
        """Test that starting a new conversation returns 201 status."""
        conversation_id = uuid4()

        # Mock the service to return a new conversation
        mock_conversation_info = ConversationInfo(
            id=conversation_id,
            agent=sample_agent,
            agent_status=AgentExecutionStatus.IDLE,
            confirmation_policy=NeverConfirm(),
        )
        mock_service.start_conversation = AsyncMock(
            return_value=(mock_conversation_info, True)
        )

        # Create request payload
        payload = {
            "agent": sample_agent.model_dump(),
            "conversation_id": str(conversation_id),
        }

        response = client.post("/api/conversations/", json=payload)

        assert response.status_code == 201
        assert response.json()["id"] == str(conversation_id)

    @patch("openhands.agent_server.conversation_router.conversation_service")
    def test_start_conversation_existing_returns_200(
        self, mock_service, client, sample_agent
    ):
        """Test that starting an existing conversation returns 200 status."""
        conversation_id = uuid4()

        # Mock the service to return an existing conversation
        mock_conversation_info = ConversationInfo(
            id=conversation_id,
            agent=sample_agent,
            agent_status=AgentExecutionStatus.IDLE,
            confirmation_policy=NeverConfirm(),
        )
        mock_service.start_conversation = AsyncMock(
            return_value=(mock_conversation_info, False)
        )

        # Create request payload
        payload = {
            "agent": sample_agent.model_dump(),
            "conversation_id": str(conversation_id),
        }

        response = client.post("/api/conversations/", json=payload)

        assert response.status_code == 200
        assert response.json()["id"] == str(conversation_id)

    @patch("openhands.agent_server.conversation_router.conversation_service")
    def test_start_conversation_without_id_returns_201(
        self, mock_service, client, sample_agent
    ):
        """Test that starting a conversation without ID returns 201 status."""
        conversation_id = uuid4()

        # Mock the service to return a new conversation
        mock_conversation_info = ConversationInfo(
            id=conversation_id,
            agent=sample_agent,
            agent_status=AgentExecutionStatus.IDLE,
            confirmation_policy=NeverConfirm(),
        )
        mock_service.start_conversation = AsyncMock(
            return_value=(mock_conversation_info, True)
        )

        # Create request payload without conversation_id
        payload = {
            "agent": sample_agent.model_dump(),
        }

        response = client.post("/api/conversations/", json=payload)

        assert response.status_code == 201
        assert response.json()["id"] == str(conversation_id)
