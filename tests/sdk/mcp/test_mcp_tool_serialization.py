"""Test MCP tool JSON serialization without discriminated unions.

MCP tools are schema-first; no 'kind' discriminator is used.
"""

from unittest.mock import Mock

import mcp.types

from openhands.sdk.mcp.client import MCPClient
from openhands.sdk.mcp.tool import MCPActionBase, MCPTool, MCPToolObservation
from openhands.sdk.tool import Tool
from openhands.sdk.tool.schema import ActionBase


def create_mock_mcp_tool(name: str = "test_tool") -> mcp.types.Tool:
    """Create a mock MCP tool for testing."""
    return mcp.types.Tool(
        name=name,
        description=f"A test MCP tool named {name}",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Query parameter"}
            },
            "required": ["query"],
        },
    )


def test_mcp_tool_json_serialization_deserialization() -> None:
    # Create mock MCP tool and client
    mock_mcp_tool = create_mock_mcp_tool()
    mock_client = Mock(spec=MCPClient)
    mcp_tool = MCPTool.create(mock_mcp_tool, mock_client)

    tool_json = mcp_tool.model_dump_json()
    deserialized_tool = MCPTool.model_validate_json(tool_json)
    assert isinstance(deserialized_tool, MCPTool)
    # We use model_dump because tool executor is not serializable and is excluded
    assert deserialized_tool.model_dump() == mcp_tool.model_dump()


def test_mcp_tool_polymorphic_behavior() -> None:
    """Test MCPTool polymorphic behavior using Tool base class."""
    # Create mock MCP tool and client
    mock_mcp_tool = create_mock_mcp_tool()
    mock_client = Mock(spec=MCPClient)

    # Create MCPTool instance
    mcp_tool = MCPTool.create(mock_mcp_tool, mock_client)

    # Should be instance of Tool
    assert isinstance(mcp_tool, Tool)
    assert isinstance(mcp_tool, MCPTool)

    # Check basic properties
    assert mcp_tool.name == "test_tool"
    assert "test MCP tool" in mcp_tool.description
    assert hasattr(mcp_tool, "mcp_tool")


# No 'kind' discriminator expectations anymore


def test_mcp_tool_fallback_behavior() -> None:
    """Test MCPTool fallback behavior with manual data."""
    # Create data that could represent an MCPTool
    tool_data = {
        "name": "fallback-tool",
        "description": "A fallback test tool",
        "input_schema": {"type": "object", "properties": {}},
        "mcp_tool": {
            "name": "fallback-tool",
            "description": "A fallback test tool",
            "inputSchema": {"type": "object", "properties": {}},
        },
    }

    deserialized_tool = Tool.model_validate(tool_data)
    assert isinstance(deserialized_tool, Tool)
    assert deserialized_tool.name == "fallback-tool"
    assert deserialized_tool.action_type is not None
    assert issubclass(deserialized_tool.action_type, ActionBase)
    assert deserialized_tool.observation_type and issubclass(
        deserialized_tool.observation_type, MCPToolObservation
    )


def test_mcp_tool_essential_properties() -> None:
    """Test that MCPTool maintains essential properties after creation."""
    # Create mock MCP tool with specific properties
    mock_mcp_tool = mcp.types.Tool(
        name="essential_tool",
        description="Tool with essential properties",
        inputSchema={
            "type": "object",
            "properties": {"param1": {"type": "string"}, "param2": {"type": "integer"}},
            "required": ["param1"],
        },
    )
    mock_client = Mock(spec=MCPClient)

    # Create MCPTool instance
    mcp_tool = MCPTool.create(mock_mcp_tool, mock_client)

    # Verify essential properties are preserved
    assert mcp_tool.name == "essential_tool"
    assert mcp_tool.description == "Tool with essential properties"
    assert mcp_tool.mcp_tool.name == "essential_tool"
    assert mcp_tool.mcp_tool.inputSchema is not None

    # Verify action type was created correctly
    assert mcp_tool.action_type is not None and issubclass(
        mcp_tool.action_type, MCPActionBase
    )
    assert hasattr(mcp_tool.action_type, "to_mcp_arguments")
