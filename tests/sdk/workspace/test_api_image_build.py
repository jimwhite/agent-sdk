"""Tests for APIRemoteWorkspace image build functionality."""

from unittest.mock import Mock, patch

import httpx
import pytest

from openhands.sdk.workspace.remote.api import APIRemoteWorkspace


@pytest.fixture
def mock_api_session():
    """Create a mock API session."""
    session = Mock(spec=httpx.Client)
    return session


@pytest.fixture
def temp_build_context(tmp_path):
    """Create a temporary build context directory with a Dockerfile."""
    build_dir = tmp_path / "build_context"
    build_dir.mkdir()

    # Create a simple Dockerfile
    dockerfile = build_dir / "Dockerfile"
    dockerfile.write_text(
        """
FROM python:3.12-slim
RUN pip install requests
CMD ["python"]
"""
    )

    return build_dir


class TestAPIRemoteWorkspaceBuild:
    """Tests for image building via Runtime API."""

    def test_build_image_via_api_success(self, temp_build_context):
        """Test successful image build via API."""
        with patch("openhands.sdk.workspace.remote.api.httpx.Client") as mock_client:
            # Mock the build initiation response
            mock_build_response = Mock()
            mock_build_response.status_code = 200
            mock_build_response.json.return_value = {"build_id": "test-build-123"}

            # Mock the build status responses (first pending, then success)
            mock_status_response_1 = Mock()
            mock_status_response_1.status_code = 200
            mock_status_response_1.json.return_value = {"status": "PENDING"}

            mock_status_response_2 = Mock()
            mock_status_response_2.status_code = 200
            mock_status_response_2.json.return_value = {
                "status": "SUCCESS",
                "image": "custom-runtime:latest",
            }

            # Mock the runtime check response (404 - no existing runtime)
            mock_runtime_check = Mock()
            mock_runtime_check.status_code = 404
            mock_runtime_check.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not found", request=Mock(), response=Mock(status_code=404)
            )

            # Mock the runtime start response
            mock_runtime_start = Mock()
            mock_runtime_start.status_code = 200
            mock_runtime_start.json.return_value = {
                "id": "runtime-123",
                "url": "http://localhost:8000",
                "api_key": "test-key",
            }

            # Setup mock client to return different responses based on the request
            mock_instance = Mock()
            mock_client.return_value = mock_instance

            def mock_request(method, url, **kwargs):
                if "/build" in url and method == "POST":
                    return mock_build_response
                elif "/build_status" in url:
                    # Return pending first time, success second time
                    if not hasattr(mock_request, "status_called"):
                        mock_request.status_called = True  # type: ignore
                        return mock_status_response_1
                    return mock_status_response_2
                elif "/sessions/" in url and method == "GET":
                    mock_runtime_check.raise_for_status()
                elif "/sessions/" in url and method == "PUT":
                    return mock_runtime_start
                return Mock()

            mock_instance.request = mock_request
            mock_instance.get = lambda url, **kwargs: mock_request("GET", url, **kwargs)
            mock_instance.post = lambda url, **kwargs: mock_request(
                "POST", url, **kwargs
            )
            mock_instance.put = lambda url, **kwargs: mock_request("PUT", url, **kwargs)

            # Patch urlopen to mock health check
            with patch("openhands.sdk.workspace.remote.api.urlopen") as mock_urlopen:
                mock_health_response = Mock()
                mock_health_response.status = 200
                mock_urlopen.return_value.__enter__.return_value = mock_health_response

                # Create workspace with build context (advanced manual configuration)
                workspace = APIRemoteWorkspace(
                    api_url="http://test-api.example.com",
                    runtime_api_key="test-key",
                    base_image="custom-runtime:latest",
                    build_context_path=str(temp_build_context),
                    build_tags=["custom-runtime:latest"],
                    working_dir="/workspace",
                    keep_alive=True,
                )

                # Verify the image was built successfully
                assert workspace.base_image == "custom-runtime:latest"

                # Clean up
                workspace.cleanup()

    def test_build_image_via_api_directly(self, temp_build_context):
        """Test calling build_image_via_api method directly."""
        with patch("openhands.sdk.workspace.remote.api.httpx.Client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance

            # Mock successful build
            mock_build_response = Mock()
            mock_build_response.status_code = 200
            mock_build_response.json.return_value = {"build_id": "test-build-456"}

            mock_status_response = Mock()
            mock_status_response.status_code = 200
            mock_status_response.json.return_value = {
                "status": "SUCCESS",
                "image": "my-image:v1.0",
            }

            mock_instance.request = Mock(
                side_effect=[mock_build_response, mock_status_response]
            )

            # Create a minimal workspace (without triggering full initialization)
            with patch.object(APIRemoteWorkspace, "model_post_init"):
                workspace = APIRemoteWorkspace(
                    api_url="http://test-api.example.com",
                    runtime_api_key="test-key",
                    base_image="base-image:latest",
                    working_dir="/workspace",
                    host="http://localhost:8000",
                )
                workspace._api_session = mock_instance
                workspace.api_url = "http://test-api.example.com"
                workspace.build_timeout = 1800.0

                # Call build_image_via_api directly
                result = workspace.build_image_via_api(
                    path=str(temp_build_context),
                    tags=["my-image:v1.0", "my-image:latest"],
                )

                assert result == "my-image:v1.0"

    def test_build_image_failure(self, temp_build_context):
        """Test build failure handling."""
        with patch("openhands.sdk.workspace.remote.api.httpx.Client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance

            # Mock build initiation
            mock_build_response = Mock()
            mock_build_response.status_code = 200
            mock_build_response.json.return_value = {"build_id": "test-build-fail"}

            # Mock build failure status
            mock_status_response = Mock()
            mock_status_response.status_code = 200
            mock_status_response.json.return_value = {
                "status": "FAILURE",
                "error": "Build failed: Dockerfile error",
            }

            mock_instance.request = Mock(
                side_effect=[mock_build_response, mock_status_response]
            )

            with patch.object(APIRemoteWorkspace, "model_post_init"):
                workspace = APIRemoteWorkspace(
                    api_url="http://test-api.example.com",
                    runtime_api_key="test-key",
                    base_image="base-image:latest",
                    working_dir="/workspace",
                    host="http://localhost:8000",
                )
                workspace._api_session = mock_instance
                workspace.api_url = "http://test-api.example.com"
                workspace.build_timeout = 1800.0

                # Expect RuntimeError on build failure
                with pytest.raises(RuntimeError, match="Build failed"):
                    workspace.build_image_via_api(
                        path=str(temp_build_context),
                        tags=["my-image:v1.0"],
                    )

    def test_image_exists(self):
        """Test image_exists method."""
        with patch("openhands.sdk.workspace.remote.api.httpx.Client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance

            # Mock image exists response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "exists": True,
                "image": {
                    "upload_time": "2024-01-01T00:00:00Z",
                    "image_size_bytes": 1024000000,
                },
            }

            mock_instance.request = Mock(return_value=mock_response)

            with patch.object(APIRemoteWorkspace, "model_post_init"):
                workspace = APIRemoteWorkspace(
                    api_url="http://test-api.example.com",
                    runtime_api_key="test-key",
                    base_image="base-image:latest",
                    working_dir="/workspace",
                    host="http://localhost:8000",
                )
                workspace._api_session = mock_instance
                workspace.api_url = "http://test-api.example.com"

                # Test image exists
                result = workspace.image_exists("my-image:v1.0")
                assert result is True

    def test_image_not_exists(self):
        """Test image_exists method when image doesn't exist."""
        with patch("openhands.sdk.workspace.remote.api.httpx.Client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance

            # Mock image not exists response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"exists": False}

            mock_instance.request = Mock(return_value=mock_response)

            with patch.object(APIRemoteWorkspace, "model_post_init"):
                workspace = APIRemoteWorkspace(
                    api_url="http://test-api.example.com",
                    runtime_api_key="test-key",
                    base_image="base-image:latest",
                    working_dir="/workspace",
                    host="http://localhost:8000",
                )
                workspace._api_session = mock_instance
                workspace.api_url = "http://test-api.example.com"

                # Test image not exists
                result = workspace.image_exists("nonexistent:latest")
                assert result is False

    def test_build_context_path_validation(self):
        """Test that invalid build context path raises ValueError."""
        with patch("openhands.sdk.workspace.remote.api.httpx.Client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance

            with patch.object(APIRemoteWorkspace, "model_post_init"):
                workspace = APIRemoteWorkspace(
                    api_url="http://test-api.example.com",
                    runtime_api_key="test-key",
                    base_image="base-image:latest",
                    working_dir="/workspace",
                    host="http://localhost:8000",
                )
                workspace._api_session = mock_instance

                # Test with non-existent path
                with pytest.raises(FileNotFoundError, match="SDK root does not exist"):
                    workspace.build_image_via_api(
                        path="/nonexistent/path",
                        tags=["my-image:v1.0"],
                    )
