"""Test for n8n integration example."""

import tempfile
from unittest.mock import Mock, patch

import pytest
from pydantic import SecretStr

from openhands.sdk import LLM, get_logger


class TestN8nIntegration:
    """Test for the n8n integration functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.logger = get_logger(__name__)

        # Mock LLM for testing
        self.mock_llm = LLM(
            model="mock-model",
            api_key=SecretStr("mock-api-key"),
        )

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("requests.post")
    def test_n8n_integration_trigger_workflow(self, mock_post):
        """Test triggering an n8n workflow."""
        # Import the integration class
        import os
        import sys

        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "examples"))

        from examples.n8n_integration_wrapper import N8nIntegration

        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "executionId": "test-execution-123",
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Create integration instance
        integration = N8nIntegration("http://localhost:5678", "test-api-key")

        # Test triggering workflow
        result = integration.trigger_workflow("test-workflow-id", {"test": "data"})

        # Verify API call was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        assert (
            call_args[0][0]
            == "http://localhost:5678/api/v1/workflows/test-workflow-id/execute"
        )
        assert call_args[1]["json"] == {"data": {"test": "data"}}
        assert call_args[1]["headers"]["X-N8N-API-KEY"] == "test-api-key"

        # Verify result
        assert result["success"] is True
        assert result["executionId"] == "test-execution-123"

    @patch("requests.get")
    def test_n8n_integration_get_executions(self, mock_get):
        """Test getting workflow executions."""
        # Import the integration class
        import os
        import sys

        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "examples"))

        from examples.n8n_integration_wrapper import N8nIntegration

        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"id": "exec-1", "status": "success"},
                {"id": "exec-2", "status": "running"},
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Create integration instance
        integration = N8nIntegration("http://localhost:5678")

        # Test getting executions
        result = integration.get_workflow_executions("test-workflow-id")

        # Verify API call was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args

        assert call_args[0][0] == "http://localhost:5678/api/v1/executions"
        assert call_args[1]["params"]["workflowId"] == "test-workflow-id"

        # Verify result
        assert len(result["data"]) == 2
        assert result["data"][0]["id"] == "exec-1"

    @patch("examples.n8n_integration_wrapper.agent")
    @patch("examples.n8n_integration_wrapper.Conversation")
    def test_n8n_integration_process_webhook_data(
        self, mock_conversation_class, mock_agent
    ):
        """Test processing webhook data with OpenHands agent."""
        # Import the integration class
        import os
        import sys

        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "examples"))

        from examples.n8n_integration_wrapper import N8nIntegration

        # Create integration instance
        integration = N8nIntegration("http://localhost:5678")

        # Mock agent to be available - create a proper Agent-like object
        from openhands.sdk.agent import Agent
        from openhands.sdk.llm import LLM

        # Create a mock LLM
        mock_llm = Mock(spec=LLM)
        mock_llm.model = "test-model"

        # Create a mock Agent with proper structure
        mock_agent_instance = Mock(spec=Agent)
        mock_agent_instance.llm = mock_llm
        mock_agent_instance.tools = []
        mock_agent_instance.system_prompt = "Test prompt"

        mock_agent_instance.agent_context = Mock()
        mock_agent_instance.tools_map = {}
        # Set the global agent variable to our mock
        mock_agent.return_value = mock_agent_instance
        # Also set it directly since it's used as a global variable
        import examples.n8n_integration_wrapper

        examples.n8n_integration_wrapper.agent = mock_agent_instance

        # Mock conversation
        from openhands.sdk.event import MessageEvent
        from openhands.sdk.llm import Message, TextContent

        mock_conversation = Mock()

        # Create a proper MessageEvent mock
        mock_message = Mock(spec=Message)
        mock_message.role = "assistant"
        mock_message.content = [
            TextContent(
                text="Processed the customer feedback successfully. Sentiment: Positive"
            )
        ]

        mock_event = Mock(spec=MessageEvent)
        mock_event.llm_message = mock_message

        # Mock the conversation state and events
        mock_conversation.state = Mock()
        mock_conversation.state.events = [mock_event]

        mock_conversation_class.return_value = mock_conversation

        # Test webhook data
        webhook_data = {
            "task": "Analyze customer feedback",
            "data": {"customer_id": "12345", "feedback": "Great product!", "rating": 5},
        }

        # Process webhook data
        result = integration.process_webhook_data(webhook_data)

        # Verify conversation was created and used
        mock_conversation_class.assert_called_once()
        mock_conversation.send_message.assert_called_once()
        mock_conversation.run.assert_called_once()

        # Verify result structure
        assert result["success"] is True
        assert "response" in result
        assert result["processed_data"] == webhook_data["data"]
        assert result["task"] == "Analyze customer feedback"

    def test_n8n_integration_process_webhook_data_error_handling(self):
        """Test error handling in webhook data processing."""
        # Import the integration class
        import os
        import sys

        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "examples"))

        from examples.n8n_integration_wrapper import N8nIntegration

        # Create integration instance
        integration = N8nIntegration("http://localhost:5678")

        # Test webhook data (agent is None during testing, so should return error)
        webhook_data = {"test": "data"}

        # Process webhook data (should handle error gracefully)
        result = integration.process_webhook_data(webhook_data)

        # Verify error was handled (agent is None during testing)
        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "OpenHands agent not available (LLM not configured)"

    def test_n8n_integration_flask_webhook_endpoint(self):
        """Test Flask webhook endpoint functionality."""
        # Skip test if Flask is not available
        import importlib.util

        if importlib.util.find_spec("flask") is None:
            pytest.skip("Flask not available")

        # Mock Flask app
        mock_app = Mock()
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.get_json.return_value = {
            "success": True,
            "response": "Test response",
            "processed_data": {"test": "data"},
        }
        mock_client.post.return_value = mock_response
        mock_app.test_client.return_value.__enter__.return_value = mock_client

        # Mock the integration processing
        with patch(
            "examples.n8n_integration_wrapper.n8n_integration"
        ) as mock_integration:
            mock_integration.process_webhook_data.return_value = {
                "success": True,
                "response": "Test response",
                "processed_data": {"test": "data"},
            }

            with patch("examples.n8n_integration_wrapper.app", mock_app):
                # Create test client
                with mock_app.test_client() as client:  # type: ignore
                    # Test webhook endpoint
                    response = client.post(
                        "/webhook/n8n",
                        json={"task": "test task", "data": {"test": "data"}},
                        content_type="application/json",
                    )

                    # Verify response
                    assert response.status_code == 200
                    response_data = response.get_json()
                    assert response_data["success"] is True
                    assert response_data["response"] == "Test response"

                    # Verify integration was called
                    mock_integration.process_webhook_data.assert_called_once()

    def test_n8n_integration_flask_trigger_endpoint(self):
        """Test Flask trigger endpoint functionality."""
        # Skip test if Flask is not available
        import importlib.util

        if importlib.util.find_spec("flask") is None:
            pytest.skip("Flask not available")

        # Mock Flask app
        mock_app = Mock()
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.get_json.return_value = {
            "success": True,
            "executionId": "test-123",
        }
        mock_client.post.return_value = mock_response
        mock_app.test_client.return_value.__enter__.return_value = mock_client

        # Mock the integration processing
        with patch(
            "examples.n8n_integration_wrapper.n8n_integration"
        ) as mock_integration:
            mock_integration.trigger_workflow.return_value = {"executionId": "test-123"}

            with patch("examples.n8n_integration_wrapper.app", mock_app):
                # Create test client
                with mock_app.test_client() as client:  # type: ignore
                    # Test trigger endpoint
                    response = client.post(
                        "/trigger/test-workflow-id",
                        json={"test": "data"},
                        content_type="application/json",
                    )

                    # Verify response
                    assert response.status_code == 200
                    response_data = response.get_json()
                    assert response_data["success"] is True
                    assert response_data["executionId"] == "test-123"

                    # Verify integration was called
                    mock_integration.trigger_workflow.assert_called_once_with(
                        "test-workflow-id", {"test": "data"}
                    )

    def test_n8n_integration_flask_health_endpoint(self):
        """Test Flask health check endpoint."""
        # Skip test if Flask is not available
        import importlib.util

        if importlib.util.find_spec("flask") is None:
            pytest.skip("Flask not available")

        # Mock Flask app
        mock_app = Mock()
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.get_json.return_value = {
            "status": "healthy",
            "n8n_base_url": "http://localhost:5678",
            "webhook_port": 8080,
        }
        mock_client.get.return_value = mock_response
        mock_app.test_client.return_value.__enter__.return_value = mock_client

        with patch("examples.n8n_integration_wrapper.app", mock_app):
            # Create test client
            with mock_app.test_client() as client:  # type: ignore
                # Test health endpoint
                response = client.get("/health")

                # Verify response
                assert response.status_code == 200
                response_data = response.get_json()
                assert response_data["status"] == "healthy"
                assert "n8n_base_url" in response_data
                assert "webhook_port" in response_data

    @patch("requests.post")
    def test_n8n_integration_api_error_handling(self, mock_post):
        """Test API error handling."""
        # Import the integration class
        import os
        import sys

        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "examples"))

        from examples.n8n_integration_wrapper import N8nIntegration

        # Mock API error
        mock_post.side_effect = Exception("Connection error")

        # Create integration instance
        integration = N8nIntegration("http://localhost:5678")

        # Test that error is properly raised
        with pytest.raises(Exception, match="Connection error"):
            integration.trigger_workflow("test-workflow-id", {"test": "data"})

    def test_n8n_integration_configuration(self):
        """Test integration configuration options."""
        # Import the integration class
        import os
        import sys

        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "examples"))

        from examples.n8n_integration_wrapper import N8nIntegration

        # Test with API key
        integration_with_key = N8nIntegration("http://localhost:5678", "test-key")
        assert integration_with_key.api_key == "test-key"
        assert integration_with_key.headers["X-N8N-API-KEY"] == "test-key"

        # Test without API key
        integration_without_key = N8nIntegration("http://localhost:5678")
        assert integration_without_key.api_key is None
        assert "X-N8N-API-KEY" not in integration_without_key.headers

        # Test base URL normalization
        integration_trailing_slash = N8nIntegration("http://localhost:5678/")
        assert integration_trailing_slash.base_url == "http://localhost:5678"

    @patch("examples.n8n_integration_wrapper.agent")
    @patch("examples.n8n_integration_wrapper.Conversation")
    def test_n8n_integration_webhook_data_processing_variations(
        self, mock_conversation_class, mock_agent
    ):
        """Test different webhook data formats."""
        # Import the integration class
        import os
        import sys

        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "examples"))

        from examples.n8n_integration_wrapper import N8nIntegration

        integration = N8nIntegration("http://localhost:5678")

        # Mock agent to be available - create a proper Agent-like object
        from openhands.sdk.agent import Agent
        from openhands.sdk.llm import LLM

        # Create a mock LLM
        mock_llm = Mock(spec=LLM)
        mock_llm.model = "test-model"

        # Create a mock Agent with proper structure
        mock_agent_instance = Mock(spec=Agent)
        mock_agent_instance.llm = mock_llm
        mock_agent_instance.tools = []
        mock_agent_instance.system_prompt = "Test prompt"

        mock_agent_instance.agent_context = Mock()
        mock_agent_instance.tools_map = {}
        # Set the global agent variable to our mock
        mock_agent.return_value = mock_agent_instance
        # Also set it directly since it's used as a global variable
        import examples.n8n_integration_wrapper

        examples.n8n_integration_wrapper.agent = mock_agent_instance

        # Mock conversation
        from openhands.sdk.event import MessageEvent
        from openhands.sdk.llm import Message, TextContent

        mock_conversation = Mock()

        # Create a proper MessageEvent mock
        mock_message = Mock(spec=Message)
        mock_message.role = "assistant"
        mock_message.content = [TextContent(text="Test response")]

        mock_event = Mock(spec=MessageEvent)
        mock_event.llm_message = mock_message

        # Mock the conversation state and events
        mock_conversation.state = Mock()
        mock_conversation.state.events = [mock_event]

        mock_conversation_class.return_value = mock_conversation

        # Test with explicit task
        result1 = integration.process_webhook_data(
            {"task": "Custom task", "data": {"key": "value"}}
        )
        assert result1["task"] == "Custom task"

        # Test without explicit task (should use default)
        result2 = integration.process_webhook_data({"data": {"key": "value"}})
        assert "Process the provided data" in result2["task"]

        # Test with no data field (should use entire payload)
        result3 = integration.process_webhook_data({"key": "value"})
        assert result3["processed_data"] == {"key": "value"}
