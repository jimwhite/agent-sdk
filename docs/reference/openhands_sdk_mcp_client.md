# openhands.sdk.mcp.client

Minimal sync helpers on top of fastmcp.Client, preserving original behavior.

## Classes

### MCPClient

Behaves exactly like fastmcp.Client (same constructor & async API),
but owns a background event loop and offers:
  - call_async_from_sync(awaitable_or_fn, *args, timeout=None, **kwargs)
  - call_sync_from_async(fn, *args, **kwargs)  # await this from async code

#### Methods

##### generate_name(name: 'str | None' = None) -> 'str'

#### Functions

##### call_async_from_sync(self, awaitable_or_fn: Union[Callable[..., Any], Any], *args, timeout: float, **kwargs)

Run a coroutine or async function on this client's loop from sync code.

Usage:
    mcp.call_async_from_sync(async_fn, arg1, kw=...)
    mcp.call_async_from_sync(coro)

##### call_sync_from_async(self, fn: Callable[..., Any], *args, **kwargs)

Await running a blocking function in the default threadpool from async code.

##### call_tool(self, name: 'str', arguments: 'dict[str, Any] | None' = None, timeout: 'datetime.timedelta | float | int | None' = None, progress_handler: 'ProgressHandler | None' = None, raise_on_error: 'bool' = True) -> 'CallToolResult'

Call a tool on the server.

Unlike call_tool_mcp, this method raises a ToolError if the tool call results in an error.

Args:
    name (str): The name of the tool to call.
    arguments (dict[str, Any] | None, optional): Arguments to pass to the tool. Defaults to None.
    timeout (datetime.timedelta | float | int | None, optional): The timeout for the tool call. Defaults to None.
    progress_handler (ProgressHandler | None, optional): The progress handler to use for the tool call. Defaults to None.

Returns:
    CallToolResult:
        The content returned by the tool. If the tool returns structured
        outputs, they are returned as a dataclass (if an output schema
        is available) or a dictionary; otherwise, a list of content
        blocks is returned. Note: to receive both structured and
        unstructured outputs, use call_tool_mcp instead and access the
        raw result object.

Raises:
    ToolError: If the tool call results in an error.
    RuntimeError: If called while the client is not connected.

##### call_tool_mcp(self, name: 'str', arguments: 'dict[str, Any]', progress_handler: 'ProgressHandler | None' = None, timeout: 'datetime.timedelta | float | int | None' = None) -> 'mcp.types.CallToolResult'

Send a tools/call request and return the complete MCP protocol result.

This method returns the raw CallToolResult object, which includes an isError flag
and other metadata. It does not raise an exception if the tool call results in an error.

Args:
    name (str): The name of the tool to call.
    arguments (dict[str, Any]): Arguments to pass to the tool.
    timeout (datetime.timedelta | float | int | None, optional): The timeout for the tool call. Defaults to None.
    progress_handler (ProgressHandler | None, optional): The progress handler to use for the tool call. Defaults to None.

Returns:
    mcp.types.CallToolResult: The complete response object from the protocol,
        containing the tool result and any additional metadata.

Raises:
    RuntimeError: If called while the client is not connected.

##### cancel(self, request_id: 'str | int', reason: 'str | None' = None) -> 'None'

Send a cancellation notification for an in-progress request.

##### close(self)

##### complete(self, ref: 'mcp.types.ResourceReference | mcp.types.PromptReference', argument: 'dict[str, str]') -> 'mcp.types.Completion'

Send a completion request to the server.

Args:
    ref (mcp.types.ResourceReference | mcp.types.PromptReference): The reference to complete.
    argument (dict[str, str]): Arguments to pass to the completion request.

Returns:
    mcp.types.Completion: The completion object.

Raises:
    RuntimeError: If called while the client is not connected.

##### complete_mcp(self, ref: 'mcp.types.ResourceReference | mcp.types.PromptReference', argument: 'dict[str, str]') -> 'mcp.types.CompleteResult'

Send a completion request and return the complete MCP protocol result.

Args:
    ref (mcp.types.ResourceReference | mcp.types.PromptReference): The reference to complete.
    argument (dict[str, str]): Arguments to pass to the completion request.

Returns:
    mcp.types.CompleteResult: The complete response object from the protocol,
        containing the completion and any additional metadata.

Raises:
    RuntimeError: If called while the client is not connected.

##### get_prompt(self, name: 'str', arguments: 'dict[str, Any] | None' = None) -> 'mcp.types.GetPromptResult'

Retrieve a rendered prompt message list from the server.

Args:
    name (str): The name of the prompt to retrieve.
    arguments (dict[str, Any] | None, optional): Arguments to pass to the prompt. Defaults to None.

Returns:
    mcp.types.GetPromptResult: The complete response object from the protocol,
        containing the prompt messages and any additional metadata.

Raises:
    RuntimeError: If called while the client is not connected.

##### get_prompt_mcp(self, name: 'str', arguments: 'dict[str, Any] | None' = None) -> 'mcp.types.GetPromptResult'

Send a prompts/get request and return the complete MCP protocol result.

Args:
    name (str): The name of the prompt to retrieve.
    arguments (dict[str, Any] | None, optional): Arguments to pass to the prompt. Defaults to None.

Returns:
    mcp.types.GetPromptResult: The complete response object from the protocol,
        containing the prompt messages and any additional metadata.

Raises:
    RuntimeError: If called while the client is not connected.

##### is_connected(self) -> 'bool'

Check if the client is currently connected.

##### list_prompts(self) -> 'list[mcp.types.Prompt]'

Retrieve a list of prompts available on the server.

Returns:
    list[mcp.types.Prompt]: A list of Prompt objects.

Raises:
    RuntimeError: If called while the client is not connected.

##### list_prompts_mcp(self) -> 'mcp.types.ListPromptsResult'

Send a prompts/list request and return the complete MCP protocol result.

Returns:
    mcp.types.ListPromptsResult: The complete response object from the protocol,
        containing the list of prompts and any additional metadata.

Raises:
    RuntimeError: If called while the client is not connected.

##### list_resource_templates(self) -> 'list[mcp.types.ResourceTemplate]'

Retrieve a list of resource templates available on the server.

Returns:
    list[mcp.types.ResourceTemplate]: A list of ResourceTemplate objects.

Raises:
    RuntimeError: If called while the client is not connected.

##### list_resource_templates_mcp(self) -> 'mcp.types.ListResourceTemplatesResult'

Send a resources/listResourceTemplates request and return the complete MCP protocol result.

Returns:
    mcp.types.ListResourceTemplatesResult: The complete response object from the protocol,
        containing the list of resource templates and any additional metadata.

Raises:
    RuntimeError: If called while the client is not connected.

##### list_resources(self) -> 'list[mcp.types.Resource]'

Retrieve a list of resources available on the server.

Returns:
    list[mcp.types.Resource]: A list of Resource objects.

Raises:
    RuntimeError: If called while the client is not connected.

##### list_resources_mcp(self) -> 'mcp.types.ListResourcesResult'

Send a resources/list request and return the complete MCP protocol result.

Returns:
    mcp.types.ListResourcesResult: The complete response object from the protocol,
        containing the list of resources and any additional metadata.

Raises:
    RuntimeError: If called while the client is not connected.

##### list_tools(self) -> 'list[mcp.types.Tool]'

Retrieve a list of tools available on the server.

Returns:
    list[mcp.types.Tool]: A list of Tool objects.

Raises:
    RuntimeError: If called while the client is not connected.

##### list_tools_mcp(self) -> 'mcp.types.ListToolsResult'

Send a tools/list request and return the complete MCP protocol result.

Returns:
    mcp.types.ListToolsResult: The complete response object from the protocol,
        containing the list of tools and any additional metadata.

Raises:
    RuntimeError: If called while the client is not connected.

##### new(self) -> 'Client[ClientTransportT]'

Create a new client instance with the same configuration but fresh session state.

This creates a new client with the same transport, handlers, and configuration,
but with no active session. Useful for creating independent sessions that don't
share state with the original client.

Returns:
    A new Client instance with the same configuration but disconnected state.

Example:
    ```python
    # Create a fresh client for each concurrent operation
    fresh_client = client.new()
    async with fresh_client:
        await fresh_client.call_tool("some_tool", {})
    ```

##### ping(self) -> 'bool'

Send a ping request.

##### progress(self, progress_token: 'str | int', progress: 'float', total: 'float | None' = None, message: 'str | None' = None) -> 'None'

Send a progress notification.

##### read_resource(self, uri: 'AnyUrl | str') -> 'list[mcp.types.TextResourceContents | mcp.types.BlobResourceContents]'

Read the contents of a resource or resolved template.

Args:
    uri (AnyUrl | str): The URI of the resource to read. Can be a string or an AnyUrl object.

Returns:
    list[mcp.types.TextResourceContents | mcp.types.BlobResourceContents]: A list of content
        objects, typically containing either text or binary data.

Raises:
    RuntimeError: If called while the client is not connected.

##### read_resource_mcp(self, uri: 'AnyUrl | str') -> 'mcp.types.ReadResourceResult'

Send a resources/read request and return the complete MCP protocol result.

Args:
    uri (AnyUrl | str): The URI of the resource to read. Can be a string or an AnyUrl object.

Returns:
    mcp.types.ReadResourceResult: The complete response object from the protocol,
        containing the resource contents and any additional metadata.

Raises:
    RuntimeError: If called while the client is not connected.

##### send_roots_list_changed(self) -> 'None'

Send a roots/list_changed notification.

##### set_elicitation_callback(self, elicitation_callback: 'ElicitationHandler') -> 'None'

Set the elicitation callback for the client.

##### set_logging_level(self, level: 'mcp.types.LoggingLevel') -> 'None'

Send a logging/setLevel request.

##### set_roots(self, roots: 'RootsList | RootsHandler') -> 'None'

Set the roots for the client. This does not automatically call `send_roots_list_changed`.

##### set_sampling_callback(self, sampling_callback: 'ClientSamplingHandler') -> 'None'

Set the sampling callback for the client.

##### sync_close(self)

