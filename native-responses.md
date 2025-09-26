GOAL: We Implement Native Responses API integration (v1, non-streaming)

Objective
- Integrate OpenAI/LiteLLM native Responses API for GPT-5 and GPT-5-mini to enable stateful conversations via previous_response_id.
- Keep Chat Completions path intact for all other models.
- Preserve Responses fidelity by using litellm.responses with typed params/returns; avoid the generic bridge that drops state.

Non-goals
- No new storage layers.
- No streaming in v1.
- Agent is minimally aware of Responses and will call llm.responses() on supported models; Chat Completions path remains for other models.

Scope (MVP)
- Non-streaming Responses only.
- Text outputs and function tool-calls.
- Persist and reuse previous_response_id for continuity.

Agreed decisions
- Gating: strictly by model. Enable only for GPT-5 and GPT-5-mini.
- Stateful flag: ConversationState.previous_response_id (None for first turn). Presence indicates a Responses conversation.
- Model switch: if previous_response_id is set and new model doesn’t support Responses, raise a strict error (TODO: relax later).
- Defaults on Responses calls: store=True, parallel_tool_calls=True.
- History: do not send prior messages; send only new input items plus previous_response_id.

Gating and mode detection
- Add supports_responses: bool to model_features with patterns ["gpt-5*", "gpt-5-mini*"].
- is_responses on a given turn = supports_responses(model) or (state.previous_response_id is not None). Agent decides the path and calls llm.responses() directly when true.

Tools
- Add Tool.to_responses_tool() that emits the Responses function tool schema (typed FunctionToolParam) matching our MCP-derived input_schema/description.
- Agent selects tool serialization per turn:
  - Responses path: [t.to_responses_tool() for t in tools].
  - Chat path: [t.to_openai_tool()].

Transport and inputs (Responses)
- Agent calls llm.responses(...) directly when in Responses mode. LLM.responses returns the typed OpenAI Response object; we do not adapt it to ModelResponse.
- LLM exposes a responses(...) method that wraps litellm.responses with typed args; it does not alter the returned type.
  - previous_response_id=state.previous_response_id (if any), store=True, parallel_tool_calls=True.
- Input construction for Responses calls (non-streaming):
  - First turn: map the first system message to instructions; map the latest user content to a Responses message input item.
  - Tool results: send as function_call_output items with call_id equal to the tool call id from the prior turn.
  - We do not replay history; continuity is carried by previous_response_id.

Agent integration
- Agent decides per turn which path to use. If is_responses is true, it calls llm.responses(...) directly and receives a typed OpenAI Response.
- When preparing the first event (system prompt), emit tools using to_responses_tool() if is_responses is true; otherwise to_openai_tool().
- Pass previous_response_id to llm.responses via kwargs.
- After each Responses call completes, set state.previous_response_id = response.id.
- Multiple tool calls in one assistant turn are already handled by Agent.step: parse Response.output for function tool calls and execute them; with parallel_tool_calls enabled this continues to work.

LLM integration
- Provide LLM.responses(...) which calls litellm.responses with typed args and returns the typed OpenAI Response unchanged.
- Keep LLM.completion(...) for non-Responses models; agent will not use completion for Responses path.
- Telemetry should still record raw typed Response for completeness.

Persistence and state
- ConversationState: add previous_response_id: str | None. This is the durable flag for Responses mode and the handle for continuation.
- Event log: continue existing events; include response.id and previous_response_id in the Telemetry logs. No new persistence structure is added.

Telemetry/Metrics
- Map Responses.usage input/output/total tokens into Metrics. If missing, use our existing token_counter fallback.
- Record response.id, previous_response_id, model, created_at, status in Telemetry (when logging enabled).

Error handling
- If previous_response_id exists but model does not supports_responses, raise a clear error (strict for v1; TODO relax later).
- If provider rejects continuation due to an invalid/expired id, clear state.previous_response_id and optionally retry once fresh (policy behind a small guard).

Tests
- Gating: GPT-5/mini routes to Responses; others route to Chat.
- Statefulness: two-call sequence with previous_response_id propagation (no history replay).
- Tool-calls: multiple function calls in one turn handled sequentially; tool result round-trip by sending function_call_output input items.
- Reasoning: reasoning content captured/persisted on events.
- Metrics: usage mapping parity with existing counters.
- Model switch error: strict error when previous_response_id set and model lacks Responses support.

Example (manual)
- Minimal example showing:
  - First call with GPT-5: system as instructions + user input; receive id and tool calls; persist state.previous_response_id.
  - Next call: send only function_call_output items + previous_response_id; receive assistant message.

Follow-ups (post-v1)
- Streaming Responses and streaming event model mapping.
- Optional richer exposure of Responses output items on events.
- Policy for relaxing strict model-switch behavior.

Typed API integration (OpenAI Responses via LiteLLM)

Sources investigated
- liteLLM integration points
  - litellm/llms/openai/openai.py (OpenAI adapter)
  - litellm/types/llms/openai.py (typed wrappers and re-exports)
- OpenAI typed models (from openai Python SDK)
  - openai.types.responses.response.Response
  - openai.types.responses.response_output_item.ResponseOutputItem
  - openai.types.responses.response_function_tool_call.ResponseFunctionToolCall
  - openai.types.responses.function_tool_param.FunctionToolParam
  - openai.types.responses.response_input_param (typed request items, e.g., FunctionCallOutput, Message variants)
  - openai.types.responses.response_create_params: Reasoning, ToolParam, ToolChoice, Text (or ResponseTextConfigParam on older SDKs)

Request typing we will use
- Tools (function schema):
  - FunctionToolParam (openai.types.responses.function_tool_param.FunctionToolParam)
    - fields: type="function", name: str, description: str | None, parameters: JSONSchema (dict), strict: bool
  - Our ToolBase.to_responses_tool() will produce FunctionToolParam with parameters=self.action_type.to_mcp_schema() and strict=True
- Inputs (non-streaming):
  - Union of typed items under openai.types.responses.response_input_param.ResponseInputParam.
  - For tool result round-trips we need FunctionCallOutput:
    - FunctionCallOutput(type="function_call_output", call_id: str, output: str)
- Optional typed params:
  - Reasoning (openai.types.responses.response_create_params.Reasoning): {effort: Literal["minimal","low","medium","high"]}
  - ToolChoice / ToolParam (for explicit tool selection if ever needed)

LLM.responses() call shape
- We will expose a typed wrapper that takes:
  - model: str
  - messages: list[Message] | list[dict] | None (only used to derive the first-call input and/or instructions)
  - tools: list[FunctionToolParam] | None
  - input: list[ResponseInputParam] | None (derived from messages or function_call_output items)
  - previous_response_id: str | None
  - store: bool = True (default)
  - parallel_tool_calls: bool = True (default)
  - reasoning: Reasoning | None (mapped from Agent/LLM config)
  - extra_body: dict | None (we’ll include metadata: model name, agent name)
- Behavior:
  - First turn: derive instructions from system Message and one message item from latest user/assistant content
  - Continuations: send only function_call_output items + previous_response_id
  - No history replay; continuity is carried by previous_response_id

Response typing and parsing
- The call returns openai.types.responses.response.Response (typed immutable model)
  - id: str — use to set state.previous_response_id for continuation
  - output: list[ResponseOutputItem] — union of textual items and tool call items
  - output_text: Optional[str] — convenience text aggregation (present in recent SDKs)
  - usage: token usage block (map to our Metrics)
  - status/created_at/model/metadata
- Tool calls:
  - ResponseFunctionToolCall items appear within Response.output
  - We will adapt these to our internal ChatCompletionMessageToolCall for Agent tool execution (name + arguments string)

Metrics/telemetry mapping
- Response.usage → MetricsSnapshot (input/output/total token counts)
- If usage missing, fall back to our token_counter on the inputs/outputs
- Log response.id and previous_response_id for continuity

Error handling (typed)
- If previous_response_id is set but supports_responses(model) == False: raise clear error and set AgentExecutionStatus.FINISHED
- If provider rejects continuation (invalid/expired id): clear state.previous_response_id; optionally retry once (policy-gated)
- Context window exceeded (when applicable): trigger condenser request flow (same policy as Chat path)

Agent integration notes (typed)
- Routing logic:
  - is_responses_mode = supports_responses(model) or state.previous_response_id is not None
  - If true → call LLM.responses(...) (typed); else → LLM.completion(...)
- Tool serialization:
  - Responses path: [t.to_responses_tool()] (FunctionToolParam)
  - Chat path: [t.to_openai_tool()] (ChatCompletionToolParam)
- Event mapping:
  - When Responses returns tool calls, emit ActionEvent(s) with llm_response_id=response.id
  - When Responses returns only text, emit MessageEvent (agent finished)

Open questions / implementation considerations
- SDK version drift:
  - Text param under response_create_params is aliased as ResponseText or ResponseTextConfigParam depending on SDK version. Make imports tolerant (try/except fallback).
- Input derivation:
  - Ensure strict typed construction of ResponseInputParam items. When messages contain list content blocks, map to {type: "message", role, content: list[parts]}
- Strict tool schema:
  - We set strict=True on FunctionToolParam to enforce parameter validation
- Parallel tool calls:
  - Keep parallel_tool_calls=True by default and preserve current Agent batching logic (thought on first, reasoning on first)

References
- LiteLLM OpenAI adapter and types
  - litellm/llms/openai/openai.py
  - litellm/types/llms/openai.py
- OpenAI Responses types in SDK
  - openai.types.responses.response.Response
  - openai.types.responses.response_input_param (FunctionCallOutput, message inputs)
  - openai.types.responses.function_tool_param.FunctionToolParam
  - openai.types.responses.response_function_tool_call.ResponseFunctionToolCall
  - openai.types.responses.response_create_params.{Reasoning, ToolParam, ToolChoice, Text}


Typed API integration (OpenAI Responses via LiteLLM)

Sources investigated
- liteLLM integration points
  - litellm/llms/openai/openai.py (OpenAI adapter)
  - litellm/types/llms/openai.py (typed wrappers and re-exports)
- OpenAI typed models (from openai Python SDK)
  - openai.types.responses.response.Response
  - openai.types.responses.response_output_item.ResponseOutputItem
  - openai.types.responses.response_function_tool_call.ResponseFunctionToolCall
  - openai.types.responses.function_tool_param.FunctionToolParam
  - openai.types.responses.response_input_param (typed request items, e.g., FunctionCallOutput, Message variants)
  - openai.types.responses.response_create_params: Reasoning, ToolParam, ToolChoice, Text (or ResponseTextConfigParam on older SDKs)

Request typing we will use
- Tools (function schema):
  - FunctionToolParam (openai.types.responses.function_tool_param.FunctionToolParam)
    - fields: type="function", name: str, description: str | None, parameters: JSONSchema (dict), strict: bool
  - Our ToolBase.to_responses_tool() will produce FunctionToolParam with parameters=self.action_type.to_mcp_schema() and strict=True
- Inputs (non-streaming):
  - Union of typed items under openai.types.responses.response_input_param.ResponseInputParam.
  - For tool result round-trips we need FunctionCallOutput:
    - FunctionCallOutput(type="function_call_output", call_id: str, output: str)
- Optional typed params:
  - Reasoning (openai.types.responses.response_create_params.Reasoning): {effort: Literal["minimal","low","medium","high"]}
  - ToolChoice / ToolParam (for explicit tool selection if ever needed)

LLM.responses() call shape
- We will expose a typed wrapper that takes:
  - model: str
  - messages: list[Message] | list[dict] | None (only used to derive the first-call input and/or instructions)
  - tools: list[FunctionToolParam] | None
  - input: list[ResponseInputParam] | None (derived from messages or function_call_output items)
  - previous_response_id: str | None
  - store: bool = True (default)
  - parallel_tool_calls: bool = True (default)
  - reasoning: Reasoning | None (mapped from Agent/LLM config)
  - extra_body: dict | None (we’ll include metadata: model name, agent name)
- Behavior:
  - First turn: derive instructions from system Message and one message item from latest user/assistant content
  - Continuations: send only function_call_output items + previous_response_id
  - No history replay; continuity is carried by previous_response_id

Response typing and parsing
- The call returns openai.types.responses.response.Response (typed immutable model)
  - id: str — use to set state.previous_response_id for continuation
  - output: list[ResponseOutputItem] — union of textual items and tool call items
  - output_text: Optional[str] — convenience text aggregation (present in recent SDKs)
  - usage: token usage block (map to our Metrics)
  - status/created_at/model/metadata
- Tool calls:
  - ResponseFunctionToolCall items appear within Response.output
  - We will adapt these to our internal ChatCompletionMessageToolCall for Agent tool execution (name + arguments string)

Metrics/telemetry mapping
- Response.usage → MetricsSnapshot (input/output/total token counts)
- If usage missing, fall back to our token_counter on the inputs/outputs
- Log response.id and previous_response_id for continuity

Error handling (typed)
- If previous_response_id is set but supports_responses(model) == False: raise clear error and set AgentExecutionStatus.FINISHED
- If provider rejects continuation (invalid/expired id): clear state.previous_response_id; optionally retry once (policy-gated)
- Context window exceeded (when applicable): trigger condenser request flow (same policy as Chat path)

Agent integration notes (typed)
- Routing logic:
  - is_responses_mode = supports_responses(model) or state.previous_response_id is not None
  - If true → call LLM.responses(...) (typed); else → LLM.completion(...)
- Tool serialization:
  - Responses path: [t.to_responses_tool()] (FunctionToolParam)
  - Chat path: [t.to_openai_tool()] (ChatCompletionToolParam)
- Event mapping:
  - When Responses returns tool calls, emit ActionEvent(s) with llm_response_id=response.id
  - When Responses returns only text, emit MessageEvent (agent finished)

Open questions / implementation considerations
- SDK version drift:
  - Text param under response_create_params is aliased as ResponseText or ResponseTextConfigParam depending on SDK version. Make imports tolerant (try/except fallback).
- Input derivation:
  - Ensure strict typed construction of ResponseInputParam items. When messages contain list content blocks, map to {type: "message", role, content: list[parts]}
- Strict tool schema:
  - We set strict=True on FunctionToolParam to enforce parameter validation
- Parallel tool calls:
  - Keep parallel_tool_calls=True by default and preserve current Agent batching logic (thought on first, reasoning on first)

References
- LiteLLM OpenAI adapter and types
  - litellm/llms/openai/openai.py
  - litellm/types/llms/openai.py
- OpenAI Responses types in SDK
  - openai.types.responses.response.Response
  - openai.types.responses.response_input_param (FunctionCallOutput, message inputs)
  - openai.types.responses.function_tool_param.FunctionToolParam
  - openai.types.responses.response_function_tool_call.ResponseFunctionToolCall
  - openai.types.responses.response_create_params.{Reasoning, ToolParam, ToolChoice, Text}

