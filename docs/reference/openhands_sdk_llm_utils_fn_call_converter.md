# openhands.sdk.llm.utils.fn_call_converter

Convert function calling messages to non-function calling messages and vice versa.

This will inject prompts so that models that doesn't support function calling
can still be used with function calling agents.

We follow format from: https://docs.litellm.ai/docs/completion/function_call

## Classes

### CacheControl

dict() -> new empty dictionary
dict(mapping) -> new dictionary initialized from a mapping object's
    (key, value) pairs
dict(iterable) -> new dictionary initialized as if via:
    d = {}
    for k, v in iterable:
        d[k] = v
dict(**kwargs) -> new dictionary initialized with the name=value pairs
    in the keyword argument list.  For example:  dict(one=1, two=2)

### TextPart

dict() -> new empty dictionary
dict(mapping) -> new dictionary initialized from a mapping object's
    (key, value) pairs
dict(iterable) -> new dictionary initialized as if via:
    d = {}
    for k, v in iterable:
        d[k] = v
dict(**kwargs) -> new dictionary initialized with the name=value pairs
    in the keyword argument list.  For example:  dict(one=1, two=2)

## Functions

### get_example_for_tools(tools: list[litellm.types.llms.openai.ChatCompletionToolParam]) -> str

Generate an in-context learning example based on available tools.

### convert_fncall_messages_to_non_fncall_messages(messages: list[dict], tools: list[litellm.types.llms.openai.ChatCompletionToolParam], add_in_context_learning_example: bool = True) -> list[dict]

Convert function calling messages to non-function calling messages.

### convert_from_multiple_tool_calls_to_single_tool_call_messages(messages: list[dict], ignore_final_tool_result: bool = False) -> list[dict]

Break one message with multiple tool calls into multiple messages.

### convert_non_fncall_messages_to_fncall_messages(messages: list[dict], tools: list[litellm.types.llms.openai.ChatCompletionToolParam]) -> list[dict]

Convert non-function calling messages back to function calling messages.

### convert_tool_call_to_string(tool_call: dict) -> str

Convert tool call to content in string format.

### convert_tools_to_description(tools: list[litellm.types.llms.openai.ChatCompletionToolParam]) -> str

### get_example_for_tools(tools: list[litellm.types.llms.openai.ChatCompletionToolParam]) -> str

Generate an in-context learning example based on available tools.

### refine_prompt(prompt: str) -> str

