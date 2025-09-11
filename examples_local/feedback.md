Reading the diff of the PR 142:

This code:
```
if get_features(self.model).supports_responses_api and not kwargs.pop(
            "force_chat_completions", False
        ):
            # Avoid Responses API when we'd mock tools
            # (i.e., native FC disabled with tools)
            if not (bool(tools) and not self.is_function_calling_active()):
                return self._responses_request(messages=messages, tools=tools, **kwargs)
```
I think, if fc is disabled, then we shouldn't care if tools are passed or not, should just call completions API.

Read carefully def _one_attempt() -> ModelResponse:
(the one inside completion())
I think you messed up and duplicated chunks of code. Or, in triplicate. Think deeply and fix it.

This code:
```
call_kwargs.setdefault("store", False)
```
should probably be in self._normalize_responses_kwargs(kwargs), isn't it a kwarg we need to set for responses API calls only?

This import:
from openhands.sdk.tool.tool import Tool as _Tool
should probably be removed, what's the point of aliasing it if we have already another Tool import? Just use that.

What's up with this code?
```
tc = out.get("tool_choice")
            if (
                isinstance(tc, dict)
                and "function" in tc
                and isinstance(tc["function"], dict)
            ):
                name = tc["function"].get("name")
                out["tool_choice"] = {"type": "function", "function": {"name": name}}
```
Isn't tool_choice for responses() the same as the tool_choice for completion()? If yes, just assign it directly, no need to check if it's a dict and all that.

In _messages_to_responses_items() function, we do call `self.format_messages_for_llm(cast(list[Message], messages))`,
but we also called it in completion() before calling _responses_request(). So we call it twice, isn't it?
```
# 1) serialize messages
        if messages and isinstance(messages[0], Message):
            messages = self.format_messages_for_llm(cast(list[Message], messages))
        else:
            messages = cast(list[dict[str, Any]], messages)
```
I think we should move the call in completion() till after checking for and forwarding to responses() and then do it in _responses_request(), since responses() can be called directly by the client code or via completion().

file:///Users/enyst/repos/agent-sdk/openhands/sdk/llm/llm.py

In non_native_fc.py:
You removed
        non_fn_message: dict = orig_msg.model_dump()
and added this:
```
        # Avoid pydantic traversal of MagicMocks (e.g., tool_calls injected by tests)
        # Build a minimal dict for the assistant message instead of model_dump().
        non_fn_message: dict = {
            "role": getattr(orig_msg, "role", "assistant"),
            "content": getattr(orig_msg, "content", None),
        }
```
This looks suspicious, why does this PR need to fix some unrelated test? The code shouldn't probably be changed, maybe
the test failure isn't happening anymore or maybe we should investigate. Please revert this change.

The function def responses_to_completion_format() seems very verbose and overly defensive. Too many hasattr() and getattr () checks. I think the two possible responses formats are well defined, and relatively similar, so I don't expect so many variations. Please simplify the code, and add type hints.

(response_converter.py)

This is silly kind of overly defensive code:
```
model_val = getattr(responses_result, "model", "")
    model = (
        model_val
        if isinstance(model_val, str)
        else (str(model_val) if model_val is not None else "")
    )
```
Just count on model, it's the *model* attribute of ModelResponse object from a MODEL PROVIDER API, it should be always a string.

This code:
```
# Extract usage information if available
    if hasattr(responses_result, "usage") and responses_result.usage is not None:
```
and all block after, is there a good reason why not write like: response["usage"] = getattr(responses_result, "usage", None)

The code block starting with: `# Ensure context_window is a non-negative int` is probably unnecessary, and unrelated. Clean up.

This import:
`from types import SimpleNamespace`
should probably be on top of the file.

