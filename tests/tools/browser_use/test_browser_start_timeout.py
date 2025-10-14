"""Test browser start timeout configuration."""

import os
from unittest.mock import MagicMock, patch

from openhands.tools.browser_use.impl import BrowserToolExecutor


def test_browser_start_timeout_default():
    """Test that browser start timeout is not set by default."""
    with (
        patch(
            "openhands.tools.browser_use.impl._ensure_chromium_available"
        ) as mock_chromium,
        patch("openhands.tools.browser_use.impl.CustomBrowserUseServer") as mock_server,
    ):
        mock_chromium.return_value = "/fake/chromium"
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance

        # Clear any existing env var
        if "TIMEOUT_BrowserStartEvent" in os.environ:
            del os.environ["TIMEOUT_BrowserStartEvent"]

        BrowserToolExecutor()

        # Should not set the env var if browser_start_timeout_seconds not provided
        assert "TIMEOUT_BrowserStartEvent" not in os.environ


def test_browser_start_timeout_custom():
    """Test that custom browser start timeout is properly set."""
    with (
        patch(
            "openhands.tools.browser_use.impl._ensure_chromium_available"
        ) as mock_chromium,
        patch("openhands.tools.browser_use.impl.CustomBrowserUseServer") as mock_server,
    ):
        mock_chromium.return_value = "/fake/chromium"
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance

        # Clear any existing env var
        if "TIMEOUT_BrowserStartEvent" in os.environ:
            del os.environ["TIMEOUT_BrowserStartEvent"]

        BrowserToolExecutor(browser_start_timeout_seconds=60)

        # Should set the env var to the custom value
        assert os.environ["TIMEOUT_BrowserStartEvent"] == "60.0"


def test_browser_start_timeout_integration():
    """Integration test to verify timeout setting is used during initialization."""
    with (
        patch(
            "openhands.tools.browser_use.impl._ensure_chromium_available"
        ) as mock_chromium,
        patch("openhands.tools.browser_use.impl.CustomBrowserUseServer") as mock_server,
    ):
        mock_chromium.return_value = "/fake/chromium"
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance

        # Clear any existing env var
        if "TIMEOUT_BrowserStartEvent" in os.environ:
            del os.environ["TIMEOUT_BrowserStartEvent"]

        # Test with 90 second timeout
        BrowserToolExecutor(browser_start_timeout_seconds=90)

        # Verify the timeout was set before server creation
        assert os.environ["TIMEOUT_BrowserStartEvent"] == "90.0"
        mock_server.assert_called_once_with(session_timeout_minutes=30)


def test_browser_start_timeout_zero():
    """Test that timeout can be set to 0 (no timeout)."""
    with (
        patch(
            "openhands.tools.browser_use.impl._ensure_chromium_available"
        ) as mock_chromium,
        patch("openhands.tools.browser_use.impl.CustomBrowserUseServer") as mock_server,
    ):
        mock_chromium.return_value = "/fake/chromium"
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance

        # Clear any existing env var
        if "TIMEOUT_BrowserStartEvent" in os.environ:
            del os.environ["TIMEOUT_BrowserStartEvent"]

        # Zero means no timeout in browser-use
        BrowserToolExecutor(browser_start_timeout_seconds=0)

        assert os.environ["TIMEOUT_BrowserStartEvent"] == "0.0"
