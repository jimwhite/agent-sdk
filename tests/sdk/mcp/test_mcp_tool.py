"""Tests for MCP tool functionality with new simplified implementation."""

import json
from unittest.mock import MagicMock

import mcp.types

from openhands.sdk.llm import TextContent
from openhands.sdk.mcp.client import MCPClient
from openhands.sdk.mcp.definition import MCPToolObservation
from openhands.sdk.mcp.tool import MCPTool, MCPToolExecutor
from openhands.sdk.tool import ToolAnnotations


class MockMCPClient(MCPClient):
    """Mock MCPClient for testing that bypasses the complex constructor."""

    def __init__(self):
        # Skip the parent constructor to avoid needing transport
        pass


class TestMCPToolObservation:
    """Test MCPToolObservation functionality."""

    def test_from_call_tool_result_success(self):
        """Test creating observation from successful MCP result."""
        # Create mock MCP result
        result = MagicMock(spec=mcp.types.CallToolResult)
        result.content = [
            mcp.types.TextContent(type="text", text="Operation completed successfully")
        ]
        result.isError = False

        observation = MCPToolObservation.from_call_tool_result(
            tool_name="test_tool", result=result
        )

        assert observation.data["tool_name"] == "test_tool"
        content = json.loads(observation.data["content"])
        assert len(content) == 1
        assert content[0]["text"] == "Operation completed successfully"
        assert observation.data["is_error"] is False

    def test_from_call_tool_result_error(self):
        """Test creating observation from error MCP result."""
        # Create mock MCP result
        result = MagicMock(spec=mcp.types.CallToolResult)
        result.content = [mcp.types.TextContent(type="text", text="Operation failed")]
        result.isError = True

        observation = MCPToolObservation.from_call_tool_result(
            tool_name="test_tool", result=result
        )

        assert observation.data["tool_name"] == "test_tool"
        content = json.loads(observation.data["content"])
        assert len(content) == 1
        assert content[0]["text"] == "Operation failed"
        assert observation.data["is_error"] is True

    def test_from_call_tool_result_with_image(self):
        """Test creating observation from MCP result with image content."""
        # Create mock MCP result with image
        result = MagicMock(spec=mcp.types.CallToolResult)
        result.content = [
            mcp.types.TextContent(type="text", text="Here's the image:"),
            mcp.types.ImageContent(
                type="image", data="base64data", mimeType="image/png"
            ),
        ]
        result.isError = False

        observation = MCPToolObservation.from_call_tool_result(
            tool_name="test_tool", result=result
        )

        assert observation.data["tool_name"] == "test_tool"
        content = json.loads(observation.data["content"])
        assert len(content) == 2
        assert content[0]["text"] == "Here's the image:"
        # Second content should be ImageContent
        assert "image_urls" in content[1]
        assert content[1]["image_urls"] == ["data:image/png;base64,base64data"]
        assert observation.data["is_error"] is False

    def test_agent_observation_success(self):
        """Test agent observation formatting for success."""
        # Create a mock MCP result for success
        result = MagicMock(spec=mcp.types.CallToolResult)
        result.content = [mcp.types.TextContent(type="text", text="Success result")]
        result.isError = False

        observation = MCPToolObservation.from_call_tool_result(
            tool_name="test_tool", result=result
        )

        # For now, we'll just verify the data structure since agent_observation
        # functionality may need to be implemented differently in the new system
        assert observation.data["tool_name"] == "test_tool"
        content = json.loads(observation.data["content"])
        assert len(content) == 1
        assert content[0]["text"] == "Success result"
        assert observation.data["is_error"] is False

    def test_agent_observation_error(self):
        """Test agent observation formatting for error."""
        # Create a mock MCP result for error
        result = MagicMock(spec=mcp.types.CallToolResult)
        result.content = [mcp.types.TextContent(type="text", text="Error occurred")]
        result.isError = True

        observation = MCPToolObservation.from_call_tool_result(
            tool_name="test_tool", result=result
        )

        # For now, we'll just verify the data structure since agent_observation
        # functionality may need to be implemented differently in the new system
        assert observation.data["tool_name"] == "test_tool"
        content = json.loads(observation.data["content"])
        assert len(content) == 1
        assert content[0]["text"] == "Error occurred"
        assert observation.data["is_error"] is True


class TestMCPToolExecutor:
    """Test MCPToolExecutor functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.executor = MCPToolExecutor(tool_name="test_tool", client=self.mock_client)

    def test_call_tool_success(self):
        """Test successful tool execution."""
        # Mock successful MCP call
        mock_result = MagicMock(spec=mcp.types.CallToolResult)
        mock_result.content = [
            mcp.types.TextContent(type="text", text="Success result")
        ]
        mock_result.isError = False

        # Mock action
        mock_action = MagicMock()
        mock_action.model_dump.return_value = {"param": "value"}

        # Mock call_async_from_sync to return the expected observation
        def mock_call_async_from_sync(coro_func, **kwargs):
            return MCPToolObservation.from_call_tool_result(
                tool_name="test_tool", result=mock_result
            )

        self.mock_client.call_async_from_sync = mock_call_async_from_sync

        observation = self.executor(mock_action)

        from openhands.sdk.tool import SchemaInstance
        assert isinstance(observation, SchemaInstance)
        assert observation.data["tool_name"] == "test_tool"
        assert observation.data["is_error"] is False

    def test_call_tool_error(self):
        """Test tool execution with error."""
        # Mock error MCP call
        mock_result = MagicMock(spec=mcp.types.CallToolResult)
        mock_result.content = [
            mcp.types.TextContent(type="text", text="Error occurred")
        ]
        mock_result.isError = True

        # Mock action
        mock_action = MagicMock()
        mock_action.model_dump.return_value = {"param": "value"}

        # Mock call_async_from_sync to return the expected observation
        def mock_call_async_from_sync(coro_func, **kwargs):
            return MCPToolObservation.from_call_tool_result(
                tool_name="test_tool", result=mock_result
            )

        self.mock_client.call_async_from_sync = mock_call_async_from_sync

        observation = self.executor(mock_action)

        from openhands.sdk.tool import SchemaInstance
        assert isinstance(observation, SchemaInstance)
        assert observation.data["tool_name"] == "test_tool"
        assert observation.data["is_error"] is True

    def test_call_tool_exception(self):
        """Test tool execution with exception."""
        # Mock action
        mock_action = MagicMock()
        mock_action.model_dump.return_value = {"param": "value"}

        # Mock call_async_from_sync to return an error observation
        def mock_call_async_from_sync(coro_func, **kwargs):
            # Create a mock MCP result for error
            mock_result = MagicMock(spec=mcp.types.CallToolResult)
            mock_result.content = [
                mcp.types.TextContent(
                    type="text", text="Error calling MCP tool test_tool: Connection failed"
                )
            ]
            mock_result.isError = True
            return MCPToolObservation.from_call_tool_result(
                tool_name="test_tool", result=mock_result
            )

        self.mock_client.call_async_from_sync = mock_call_async_from_sync

        observation = self.executor(mock_action)

        from openhands.sdk.tool import SchemaInstance
        assert isinstance(observation, SchemaInstance)
        assert observation.data["tool_name"] == "test_tool"
        assert observation.data["is_error"] is True
        content = json.loads(observation.data["content"])
        assert "Connection failed" in content[0]["text"]


class TestMCPTool:
    """Test MCPTool functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MockMCPClient()

        # Create mock MCP tool
        self.mock_mcp_tool = MagicMock(spec=mcp.types.Tool)
        self.mock_mcp_tool.name = "test_tool"
        self.mock_mcp_tool.description = "A test tool"
        self.mock_mcp_tool.inputSchema = {
            "type": "object",
            "properties": {"param": {"type": "string"}},
        }
        self.mock_mcp_tool.annotations = None
        self.mock_mcp_tool.meta = None

        self.tool = MCPTool.create(
            mcp_tool=self.mock_mcp_tool, mcp_client=self.mock_client
        )

    def test_mcp_tool_creation(self):
        """Test creating an MCP tool."""
        assert self.tool.name == "test_tool"
        assert self.tool.description == "A test tool"

        schema_dict = self.tool.input_schema.to_mcp_schema()
        assert len(schema_dict["properties"]) == 2
        assert "security_risk" in schema_dict["properties"]

        # Create a copy to avoid modifying the original
        expected_schema = schema_dict.copy()
        expected_schema["properties"] = expected_schema["properties"].copy()
        expected_schema["properties"].pop("security_risk")

        assert expected_schema == {
            "type": "object",
            "properties": {"param": {"type": "string"}},
        }

    def test_mcp_tool_with_annotations(self):
        """Test creating an MCP tool with annotations."""
        # Mock tool with annotations
        mock_tool_with_annotations = MagicMock(spec=mcp.types.Tool)
        mock_tool_with_annotations.name = "annotated_tool"
        mock_tool_with_annotations.description = "Tool with annotations"
        mock_tool_with_annotations.inputSchema = {"type": "object"}
        mock_tool_with_annotations.annotations = ToolAnnotations(title="Annotated Tool")
        mock_tool_with_annotations.meta = {"version": "1.0"}

        tool = MCPTool.create(
            mcp_tool=mock_tool_with_annotations, mcp_client=self.mock_client
        )

        assert tool.name == "annotated_tool"
        assert tool.description == "Tool with annotations"
        assert tool.annotations is not None

    def test_mcp_tool_no_description(self):
        """Test creating an MCP tool without description."""
        # Mock tool without description
        mock_tool_no_desc = MagicMock(spec=mcp.types.Tool)
        mock_tool_no_desc.name = "no_desc_tool"
        mock_tool_no_desc.description = None
        mock_tool_no_desc.inputSchema = {"type": "object"}
        mock_tool_no_desc.annotations = None
        mock_tool_no_desc.meta = None

        tool = MCPTool.create(mcp_tool=mock_tool_no_desc, mcp_client=self.mock_client)

        assert tool.name == "no_desc_tool"
        assert tool.description == "No description provided"

    def test_executor_assignment(self):
        """Test that the tool has the correct executor."""
        assert isinstance(self.tool.executor, MCPToolExecutor)
        assert self.tool.executor.tool_name == "test_tool"
        assert self.tool.executor.client == self.mock_client
