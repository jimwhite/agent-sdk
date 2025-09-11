"""Tests for the simplified proxy implementation."""

from unittest.mock import Mock, patch

from pydantic import SecretStr

from openhands.sdk.agent import Agent
from openhands.sdk.client.proxy import Proxy
from openhands.sdk.conversation import Conversation
from openhands.sdk.llm import LLM


class TestSimplifiedProxy:
    """Test the simplified proxy implementation."""

    def test_proxy_initialization(self):
        """Test proxy can be initialized with correct parameters."""
        proxy = Proxy(url="http://localhost:9000", api_key="test-key")
        assert proxy.base_url == "http://localhost:9000"
        assert proxy.api_key == "test-key"
        assert proxy.timeout == 30.0

    def test_proxy_initialization_strips_trailing_slash(self):
        """Test proxy strips trailing slash from URL."""
        proxy = Proxy(url="http://localhost:9000/", api_key="test-key")
        assert proxy.base_url == "http://localhost:9000"

    @patch("httpx.Client")
    def test_health_check(self, mock_client_class):
        """Test health check makes correct request."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"status": "alive"}
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        proxy = Proxy(url="http://localhost:9000", api_key="test-key")
        result = proxy.health_check()

        assert result == {"status": "alive"}
        mock_client.get.assert_called_once_with("http://localhost:9000/alive")

    def test_import_conversation_class(self):
        """Test importing Conversation class returns proxy version."""
        proxy = Proxy(url="http://localhost:9000", api_key="test-key")
        ProxyConversation = proxy.import_(Conversation)

        assert ProxyConversation != Conversation
        assert callable(ProxyConversation)

    def test_import_agent_class(self):
        """Test importing Agent class returns proxy version."""
        proxy = Proxy(url="http://localhost:9000", api_key="test-key")
        ProxyAgent = proxy.import_(Agent)

        assert ProxyAgent != Agent
        assert callable(ProxyAgent)

    def test_import_llm_class(self):
        """Test importing LLM class returns proxy version."""
        proxy = Proxy(url="http://localhost:9000", api_key="test-key")
        ProxyLLM = proxy.import_(LLM)

        assert ProxyLLM != LLM
        assert callable(ProxyLLM)

    def test_import_any_class_works(self):
        """Test importing any class works with generic proxy."""
        proxy = Proxy(url="http://localhost:9000", api_key="test-key")

        class CustomClass:
            pass

        # With the generic proxy, any class should work
        ProxyClass = proxy.import_(CustomClass)
        assert ProxyClass is not None

    def test_proxy_llm_model_dump(self):
        """Test proxy LLM model_dump returns configuration."""
        proxy = Proxy(url="http://localhost:9000", api_key="test-key")
        ProxyLLM = proxy.import_(LLM)

        llm = ProxyLLM(model="test-model", api_key=SecretStr("test-key"))
        config = llm.model_dump()

        assert config == {"model": "test-model", "api_key": SecretStr("test-key")}

    def test_conversation_proxy_creation(self):
        """Test creating conversation proxy works."""
        proxy = Proxy(url="http://localhost:9000", api_key="test-key")
        ProxyConversation = proxy.import_(Conversation)

        conversation = ProxyConversation()  # type: ignore[call-arg]

        # Should be able to create instances
        assert conversation is not None
        assert hasattr(conversation, "send_message")

    def test_context_manager(self):
        """Test proxy can be used as context manager."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            with Proxy(url="http://localhost:9000", api_key="test-key") as proxy:
                assert proxy is not None

            # Should close the client
            mock_client.close.assert_called_once()


class TestConversationProxy:
    """Test the ConversationProxy functionality."""

    @patch("httpx.Client")
    def test_conversation_proxy_creation(self, mock_client_class):
        """Test creating conversation proxy works."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        proxy = Proxy(url="http://localhost:9000", api_key="test-key")
        ProxyConversation = proxy.import_(Conversation)
        conversation = ProxyConversation()  # type: ignore[call-arg]

        # Should be able to create instances
        assert conversation is not None
        # The proxy should have the original class methods available
        assert hasattr(conversation, "send_message")

    @patch("httpx.Client")
    def test_conversation_special_case(self, mock_client_class):
        """Test that Conversation gets special ConversationProxy treatment."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        proxy = Proxy(url="http://localhost:9000", api_key="test-key")
        ProxyConversation = proxy.import_(Conversation)

        # Conversation should get special proxy treatment, not generic proxy
        conversation = ProxyConversation()  # type: ignore[call-arg]

        # Should have ConversationProxy methods
        assert hasattr(conversation, "send_message")
        # The instance should be a ConversationProxy, not a GenericProxy
        assert "ConversationProxy" in conversation.__class__.__name__
