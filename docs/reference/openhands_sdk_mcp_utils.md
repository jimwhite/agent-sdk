# openhands.sdk.mcp.utils

Utility functions for MCP integration.

## Functions

### create_mcp_tools(config: dict | fastmcp.mcp_config.MCPConfig, timeout: float = 30.0) -> list[openhands.sdk.tool.tool.Tool]

Create MCP tools from MCP configuration.

### log_handler(message: mcp.types.LoggingMessageNotificationParams)

Handles incoming logs from the MCP server and forwards them
to the standard Python logging system.

