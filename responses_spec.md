Title: Responses API Integration Spec (Agent SDK)
Status: Draft (for review)
Last updated: 2025-10-02

References
- Local LiteLLM (installed in this repo):
  • .venv/lib/python3.12/site-packages/litellm/responses/main.py (responses(), aresponses(), delete/get/list helpers)
  • .venv/lib/python3.12/site-packages/litellm/responses/utils.py (ResponsesAPIRequestUtils)
  • .venv/lib/python3.12/site-packages/litellm/llms/base_llm/responses/transformation.py (BaseResponsesAPIConfig, transformation handler)
  • .venv/lib/python3.12/site-packages/litellm/types/llms/openai.py (ResponseInputParam, ResponsesAPIResponse, ToolParam, ToolChoice, Reasoning, PromptObject, ResponseIncludable)
- Project files in this repository:
  • openhands/sdk/llm/message.py (Message, MessageToolCall, reasoning/thinking fields)
  • openhands/sdk/llm/llm.py (LLM adapter; add responses() path)
  • responses_spec.md (this document)
  • examples/25_responses_readme_summary.py (reference example)
- External documentation:
  • OpenAI Responses API: https://platform.openai.com/docs/api-reference/responses

1) Objective

Add an alternative LLM invocation path using OpenAI’s Responses API (via LiteLLM), alongside the existing Chat/Completions path. Preserve a single uniform return type (LLMResponse) and consistent Agent tool-calling behavior. Prefer strong typing via LiteLLM types; avoid untyped dicts and defensive fallbacks.

Key outcomes:
- Enable Responses API for gpt-5 (see model_features.py)
- Add llm.responses() with a signature mirroring completion() semantics
- Route Agent calls to Completions vs Responses path by model features
- Unify tool-calling loop for both paths, with a strongly-typed ToolCall wrapper
- Support non-stream first; design streaming to follow
- Telemetry includes path and usage from Response objects
- Minimal code surface change visible to callers (Agent APIs unchanged)


2) Background: OpenAI Responses API (short)

The Responses API is OpenAI’s unified interface for model responses across modalities and tools.

Important points relevant to us:
- Endpoint semantics: POST /v1/responses returns a Response object with output items (message, tool calls, etc.). Streaming uses a rich Server-Sent Events set (response.created, response.output_text.delta, response.function_call_arguments.delta, …).
- Inputs: “input” (string or structured), “instructions” (system/dev prompt), “tools” (built-in and function tools), “tool_choice”, “reasoning” config (gpt-5, o-series), “include” supports things like reasoning.encrypted_content, message.output_text.logprobs, etc.
- Outputs: Response object includes output array with items (e.g., a message with output_text), usage stats, reasoning, etc.
- Multi-turn: stateful usage implies using previous_response_id or conversation objects; also stateless usage + “include: [reasoning.encrypted_content]” to pass encrypted reasoning across turns as needed.
- Function calling: returns function call arguments (streamed as delta/done events; non-streaming shape may return function/tool call items in output array).
- Differences vs Chat Completions: The Responses API returns items rather than a single message; supports richer tool modalities and new fields (reasoning config, encrypted reasoning, parallel tool calls, etc.).

2.1 Supported input/output shape (concise, typed)

Inputs (Requests)
- instructions: str | None
- input: list[InputItem]
  - InputTextItem: {"type": "input_text", "text": str}
  - InputImageItem (v1 scope documented below):
    • URL form: {"type": "input_image", "image_url": str}
    • File-id form (future): {"type": "input_image", "image_file_id": str}
    • Base64 form (future): {"type": "input_image", "image_b64": str, "mime_type": str}
- tools: list[FunctionTool]
  - FunctionTool: {"type": "function", "function": {"name": str, "description": str | None, "parameters": JSONSchemaObject}}
- tool_choice: Literal["auto","none","required"] | {"type":"function","function":{"name": str}}
- reasoning (gpt-5/o-series only): {"effort": Literal["minimal","low","medium","high"]} | None
- include: list[str] | None (e.g., ["reasoning.encrypted_content"])
- generation params: temperature: float | None, top_p: float | None, max_output_tokens: int | None, parallel_tool_calls: bool | None
- store: bool | None
- metadata: dict[str,str] | None
- stream: bool

Outputs (Response object — subset consumed by SDK)
- id: str
- status: Literal["completed","failed","in_progress","cancelled","queued","incomplete"]
- model: str
- usage: {"input_tokens": int, "output_tokens": int, "total_tokens": int, ...}
- output: list[ResponseOutputItem], where we consume:
  - AssistantMessageItem:
    {"type":"message","role":"assistant","content":[OutputTextPart | ...], "status":"completed" | "in_progress", "id": str}
  - (If present for non-streaming) Function/Tool call items; shape may vary by provider; we normalize to MessageToolCall (see §4.7)
- reasoning: {"effort": str | None, "summary": str | None} | None
- previous_response_id: str | None

Output content parts consumed
- OutputTextPart: {"type": "output_text", "text": str, "annotations": list}
- (Future) refusal/logprobs etc. are ignored unless explicitly requested via include.

Images
- Inputs: supported as InputImageItem (see §4.8). V1 default only URL form is enabled.
- Outputs: assistant textual outputs only in v1. Image generation/streaming is handled by Images APIs or tool outputs, not by default message.output_text.

2.2 Reasoning object fields (subset we consume)
From OpenAI docs, a reasoning item has:
- type: "reasoning"
- id: string — unique identifier of the reasoning content
- summary: array — reasoning summary content
- content: array — reasoning text content
- encrypted_content: string — populated when include contains "reasoning.encrypted_content"
- status: "in_progress" | "completed" | "incomplete" — present when items are returned via API

Policy:
- When include requests reasoning.encrypted_content and it is returned, we store the encrypted payload and, if manually managing context, include these reasoning items unchanged in the next Responses request input (as supported by LiteLLM types) so the model can continue its chain-of-thought context. We never log encrypted content.

3) High-level Design

3.1 Routing strategy (Agent → LLM path)
- Introduce supports_responses_api(model: str) -> bool using model_features.py.
  - At minimum: return True for gpt-5 family (and any future Responses-first models).
- Agent decides which path to use:
  1) If supports_responses_api(model) is True, use Responses.
  2) Else, fallback to existing completion() path.
- The Agent-facing API remains unchanged; the Agent builds Message(s) and tool specs the same way. Internally we translate to the appropriate LiteLLM request.

3.2 New llm.responses() method
Add a method parallel to the existing completion(), with near-identical call semantics, returning LLMResponse.

Proposed (sync to mirror existing llm.py conventions):
# REMAKE this to mirror llm.py completion() signature -ish, as appropriate. We don't need to repeat the LLM attributes.
- def responses(
    self,
    messages: list[Message],
    tools: Sequence[ToolBase] | None = None,
    include: list[str] | None = None,                        # e.g. ["reasoning.encrypted_content"]
    store: bool | None = None,                               # default False in SDK
    return_metrics: bool = False,
    add_security_risk_prediction: bool = False,
    **kwargs,
  ) -> LLMResponse

Notes:
- Signature mirrors completion() but maps parameters to Responses API (“instructions”, “input”, “tools”, etc.). We keep naming aligned with our SDK, translating internally.
- messages: We will concatenate/structure to create Responses “input” and “instructions”:
  - The “system/developer” content goes into instructions
  - The rest goes into “input” as an array of input_text entries (see 4.2)
- tools/tool_choice map to Responses equivalents.
- include allows “reasoning.encrypted_content” to be requested if the user opts-in.
- stream: Non-stream first milestone; streaming support follows with event handling.
- Implementation note: To trigger LiteLLM Responses mode with the installed LiteLLM version, llm.responses() will call litellm.responses(), with a model set to e.g. "openai/gpt-5-mini", and maybe store=True, for which liteLLM has a config which chooses the /responses endpoint; so liteLLM sends to OpenAI’s /responses endpoint. We do NOT use LiteLLM’s responses_api_bridge; we do not hand-craft HTTP calls. Import path: from litellm.responses.main import responses (and in the future, aresponses for async).

3.3 Reuse LLMResponse
We already have:
class LLMResponse(BaseModel):
  message: Message
  metrics: MetricsSnapshot
  raw_response: ModelResponse | ResponsesAPIResponse

We’ll:
- Continue returning LLMResponse for both paths.
- Set raw_response to ResponsesAPIResponse when using Responses path.
- For message: map Responses output items to a single SDK Message (see 4.3).
- For metrics: map usage + response time; include optional encrypted reasoning passthrough if we decide to expose it in metrics or a future field.

3.4 Strong typing with LiteLLM
- Rely on LiteLLM’s explicit types and clients:
  - Non-stream: litellm.responses(...) → ResponsesAPIResponse
  - Stream (later): litellm.responses_stream(...) → event stream types
- Avoid dict soup. Parse structured fields into our SDK types (Message, ToolCall, MetricsSnapshot).

3.5 Tool calling loop (Agent)
- Unify tool execution flow for Completions and Responses:
  - For the Responses path, detect tool call outputs (see 4.4) and call the appropriate agent tool handler(s).
  - Use Message.tool_calls: list[MessageToolCall] (defined in openhands.sdk.llm.message) to hold normalized tool calls for both paths; set origin to "completion" or "responses" and keep the raw provider object (ChatCompletionMessageToolCall | ResponseFunctionToolCall) for advanced consumers.
  - Always propagate provider-supplied call_id for each tool/function call and use it as the primary identifier of the call. When submitting tool outputs back to the model, pass this value as tool_call_id.
- Maintain parity with current tool loop (naming, behavior), just a different source.

3.6 Telemetry
- Add a “llm_path” dimension: “completions” vs “responses”
- Capture model, token usage, errors, latency
- Ensure usage mapping from ResponsesAPIResponse.usage fields (input_tokens, output_tokens, total_tokens) populates MetricsSnapshot consistently.

3.7 Non-goals (initially)
- Built-in OpenAI tools (web search, file search, computer use) are out-of-scope for v1; we focus on function-calling parity with existing Agent tools.
- Conversation APIs and background runs are out-of-scope initially. We keep our Agent loop stateless, optionally passing along encrypted reasoning when requested.


4) Mapping and Data Shapes

4.1 Model feature detection
- Add supports_responses_api(model: str) using model_features.py (e.g., “gpt-5” → True, others False unless explicitly enabled).
- Keep a centralized table so we can gradually add models that should use Responses by default.

4.2 Building a Responses request from our Message list
- Existing SDK feeds: a list of Message objects with role in {system, developer, user, assistant, tool}.
- Mapping policy:
  - 1 system/developer Message → instructions (string). If multiple, concatenate with clear separators.
  - user/assistant/tool turns → Responses “input” items; For v1 we’ll convert all to text (input_text) where applicable. Images/audio/file inputs not in scope for v1 unless already supported in Agent (we can extend later).
  - tools: Convert each Tool (ToolBase) to Responses function tool schema via a new Tool API method (see §4.7.1).
  - tool_choice: map to Responses tool_choice (auto/none/required or specific function).
- Example request sketch:
  litellm.responses(
    model=model_id,
    instructions=system_str,
    input=[{"type": "input_text", "text": user_text}, ...],
    tools=[...],
    store=False,  # default for SDK
  )
  Note that temperature is always 1 for gpt-5*.
  If enable_encrypted_reasoning is True and the model supports it, set include=["reasoning.encrypted_content"].
  Implementation note: We send the request to litellm responses() with the (messages, tool role items) in the Responses API wire format (ResponseCreateParams?), including function_call_output items for tool results. Read litellm responses() code to see how it maps to OpenAI /responses endpoint.

4.2.1 Message → ResponseInputParam mapping (v1)
- instructions:
  • Concatenate Message(role in {"system","developer"}) TextContent into a single string with clear separators; assign to instructions.
- input (ResponseInputParam list):
  • User turns: {"type":"message","role":"user","content":[{"type":"input_text","text":"..."} ...]}
  • Assistant prior turns (stateless carry-in): emit {"type":"input_text","text":"<assistant text>"} items (assistant role not used in ResponseInputParam.Message)
  • Tool execution results (follow-up): {"type":"function_call_output","call_id":"<id>","output":"<JSON string>"} (one per tool call)
  • Image inputs via URL: {"type":"input_image","image_url":"<url>"} for each ImageContent URL (detail optional; use "auto" for default provider behavior)
- tools:
  • Build OpenAI ToolParam objects (type="function", function: {name, description?, parameters(JSON Schema)}); implement ToolBase.to_responses_tool() to produce this shape. FYI we do need the schema.
- tool_choice:
  • Pass "auto" | "none" | "required" or a named function per OpenAI ToolChoice
- reasoning:
  • If LLM.reasoning_effort in {"low","medium","high"} and model supports reasoning, set {"effort": value}; else omit
- sampling and limits:
  • max_output_tokens → max_output_tokens
  • For gpt-5 family, temperature is effectively 1 (provider-enforced); ignore overrides
- metadata/store:
  • metadata conforms to OpenAI Metadata (≤16 key/value pairs, string:string)
  • store defaults False in SDK (stateless); when enable_encrypted_reasoning is True, request include=["reasoning.encrypted_content"]

4.3 Mapping Responses output → SDK Message
- Non-stream:
  - Response.output is an array of items. Select the first assistant "message" item whose content contains output_text parts; concatenate those parts to a single string for Message.content.
  - If multiple assistant messages exist, select the first with status="completed". If none are completed, select the first assistant item.
  - Set LLMResponse.message to that assistant Message; if no assistant text exists, create an assistant Message with empty content (tool-call-only step).
- Assistant output shape in v1: Message carries only text content; other response item types (e.g., image generation results) are not surfaced on Message and remain available via LLMResponse.raw_response.
- Usage:
  - Map Response.usage.input_tokens, output_tokens, total_tokens to MetricsSnapshot. If a reasoning_tokens field exists, place it in MetricsSnapshot.extras["reasoning_tokens"].
- Reasoning:
  - See §2.2 for fields (type, id, summary, content, encrypted_content, status). Do not log presence or content.

  - If include contains “reasoning.encrypted_content” and a payload is present, store it as part of the Action (which will serialize it in conversation state) for pass-back on a subsequent turn (never log it).
- Output items we consume (OpenAI types, coming to us via liteLLM wrapper types with the same name - verify this):
  • ResponseOutputMessage (type="message"): concatenate content parts of type "output_text"
  • ResponseFunctionToolCall (type="function_call"): map to MessageToolCall with id=call_id, name=function.name, arguments=function.arguments (string JSON), origin="responses", raw=ResponseFunctionToolCall
  • ResponseReasoningItem (type="reasoning"): retain encrypted_content if requested; store in Action and display in the visualizer plaintext reasoning content if any; same for summary items.
  • Populate Message.responses_reasoning_item with a typed mirror of ResponseReasoningItem (id, summary[], content[], encrypted_content, status) for full‑fidelity preservation.
4.3.1 Action and Visualizer integration (Responses)
- Persist in ActionEvent (serialized in conversation state):
  • reasoning_summaries: list[str] extracted from Response.reasoning.summary (when present)
  • reasoning_blocks: list[str] aggregated from ResponseReasoningItem content text parts (when present)
  • encrypted_reasoning: str | None containing reasoning.encrypted_content when include requested; never logged
- On subsequent turns, when enable_encrypted_reasoning is True and encrypted_reasoning exists, include it unchanged in the next Responses request input per OpenAI guidance to preserve reasoning context.
- Visualizer rendering:
  • Show a “Reasoning” section (plaintext) for reasoning_blocks and reasoning_summaries when present
  • Never render encrypted_reasoning content
- Tool-call identifiers:
  • Use provider call_id as the canonical identifier across ActionEvent and ObservationEvent; submit tool results with function_call_output items using that call_id.
  Other output item types (computer/file/web search/mcp/code_interpreter, etc.) are ignored in v1.

Note on reasoning cardinality:
- The OpenAI Responses API returns Response.output as a list of items, and ResponseReasoningItem is one possible union member. While non-streaming commonly yields 0 or 1 reasoning item, the schema permits multiple items and streaming can surface multiple reasoning-related events that may materialize as one or more final items. 
- For v1 simplicity (non‑stream), Message.responses_reasoning_item is modeled as a single ReasoningItemModel | None. If multiple reasoning items are ever returned, we will select the first completed item.

4.4 Mapping tool calls (function calling)
- Streaming (later): function_call_arguments.delta/done events carry arguments; for non-streaming, LiteLLM may return tool/function calls in the final Response output (implementation detail varies).
- v1 approach (non-streaming):
  - If the final Response contains function/tool call items, map each to a normalized MessageToolCall with:
    - name (function name)
    - arguments_json (string JSON)
    - call_id (string) — use the provider-supplied id. For OpenAI:
      • Responses API: use call_id from the function/tool call item or event
      • Chat Completions: use tool_calls[i].id
  - The Agent tool loop executes these against our registered tools, collects tool outputs, and triggers a follow-up model turn.
  - Submission back to the model:
    - Completions path: include a tool role message with tool_call_id set to MessageToolCall.call_id (already implemented); this is already implemented for all tool calls that the model requested.
    - Responses path: add ResponseInputParam items of type "function_call_output" to the next responses request input, one per tool call result:
      {"type":"function_call_output","call_id": MessageToolCall.call_id, "output": "<JSON string>"}
- v1 notes:
  - We treat call_id as the stable identifier across turns; we do not synthesize ids when a provider supplies one. Providers we target (OpenAI) include these ids.

4.5 Error handling
- Rely on LiteLLM’s typed exceptions.
- Map OpenAI error/status → our LLMError categories for telemetry.

4.6 Streaming (phase 2)
- Responses streaming uses event types (response.created, response.output_text.delta, response.function_call_arguments.delta, etc.).
- Plan:
  - Add llm.responses(stream=True) that yields SDK StreamingEvents (mirroring our chat streaming abstraction).
  - For tool-calls-over-stream, accumulate arguments via function_call_arguments.delta and emit ToolCallRequested events when done, then pause stream until tool outputs are submitted.
  - This is a follow-up milestone; v1 delivers non-stream parity.

4.7 Explicit type definitions (SDK + mapping)

4.7.1 SDK-facing types (reuse existing)

- Message: use openhands.sdk.llm.message.Message (content is Sequence[TextContent | ImageContent]; includes tool_calls: list[MessageToolCall] | None, tool_call_id, name, reasoning_content, thinking_blocks). Add responses_reasoning_item: ReasoningItemModel | None to mirror OpenAI ResponseReasoningItem (id, summary[list[str]], content[list[str]] | None, encrypted_content: str | None, status). Also add reasoning_summaries: Sequence[str] | None and reasoning_blocks: Sequence[str] | None for convenience and visualization. Continue to display plaintext summaries/blocks in the visualizer; never render encrypted_content. 
- Content parts: use TextContent and ImageContent from message.py; no new content types.
- Tool calls (normalized wrapper for Agent loop): define MessageToolCall internally with:
  • name: str
  • arguments_json: str
  • call_id: str | None
  • source_path: Literal["completions","responses"]
- Tool specs: existing completion() implementation uses existing Tool classes’ to_openai_tool() which yields ChatCompletionToolParam. For Responses, create a new method to_responses_tool() that maps to the correct Responses tool schema.
- Tool choice: "auto" | "none" | "required" but 'auto' is fine by default, just like completion().
- Metrics: reuse openhands.sdk.llm.utils.metrics.MetricsSnapshot.
- LLMResponse: reuse openhands.sdk.llm.llm_response.LLMResponse with raw_response: ModelResponse | ResponsesAPIResponse.
- Reasoning effort: use LLM.reasoning_effort (low|medium|high|none) and translate to Responses.reasoning={"effort": ...}. Default to 'high'.

4.7.2 Responses request/response mapping (subset we consume)

# Request (LiteLLM constructs wire shape; we build typed inputs for litellm.responses)
- instructions: built by concatenating system/developer Messages (with clear separators).
- input: array of input items derived from Message list:
  • user/assistant/tool textual turns → {"type":"input_text","text": "..."} items
  • ImageContent (v1): URL form only → {"type":"input_image","image_url":"..."}
- tools: from Tool.to_openai_tool() JSON schema; for Responses we pass function tools with identical schema.
- tool_choice: pass through as Union["auto","none","required"] or named function.
- reasoning: if LLM.reasoning_effort in {"low","medium","high"} and model supports reasoning, send {"effort": that value}. If "none" or unsupported, omit reasoning.
- sampling params: mirror completion() policy. When get_features(model).supports_reasoning_effort is True (e.g., gpt-5), drop/ignore temperature and top_p (provider may fix temperature=1).
- metadata: per-call dict[str,str], merged with LLM.metadata and passed through to LiteLLM for provider tracing only.
- parallel_tool_calls, store, include: forwarded as provided (include may contain "reasoning.encrypted_content").
- tool outputs (follow-up turns): for Responses, add input items of type "function_call_output" per OpenAI Responses API:
  {"type":"function_call_output","call_id": MessageToolCall.call_id, "output": "<JSON string>"}.

# Response (LiteLLM typed ResponsesAPIResponse; we consume a subset)
- Select first assistant "message" item with output_text parts; concatenate to build the assistant Message.content (text-only v1).
- Extract tool/function calls from non-stream output items when present; normalize each to MessageToolCall capturing name, arguments_json, and call_id.
- usage → MetricsSnapshot (input_tokens, output_tokens, total_tokens).
- reasoning:
  • If include requested encrypted_content and it is present, store it as part of the Action (persisted in conversation state) for pass-back on a subsequent turn (never log it).
  • previous_response_id may be stored if/when we support stateful flows (out-of-scope for v1).

Notes:
- We deliberately model only the fields we consume and keep raw_response for full access/debugging.
- Tool calls in non-stream mode may appear as provider-specific items; we extract name/arguments to MessageToolCall when present.

4.8 Images support (policy and mapping)

Scope v1:
- Inputs:
  - Supported: Image via URL only (ImageContent with source="url", url set).
  - Mapping: For each ImageContent, emit InputImageItemURL in Responses “input”.
- Not supported initially:
  - Local bytes/base64 or file uploads; we will add:
    • Base64 form mapping to InputImageItemB64
    • File upload → Files API then InputImageItemFileId
- Outputs:
  - Assistant outputs remain text-only Message in v1. Other output items (e.g., image generation results) are preserved in LLMResponse.raw_response but not surfaced on Message. If the model/tool returns images (via a tool), our Agent tool loop can handle it as a tool result; not part of v1 LLMResponse.message.

Design rationale:
- Keep v1 simple and typed: text-first with optional image inputs via URL.
- Extend safely later without breaking types by adding new MessagePart variants and mapping rules.

5) Public/SDK Surface

5.1 New APIs
- In llm.py:
  - def supports_responses_api(model: str) -> bool
  - def responses(...same shape as completion()...) -> LLMResponse

5.2 Existing types reused
- LLMResponse (already supports raw_response: ModelResponse | ResponsesAPIResponse)
- Message
- MetricsSnapshot

5.3 New internal types
- MessageToolCall (wrapper)
  - name: str
  - arguments_json: str
  - call_id: str | None
  - source_path: Literal["completions", "responses"]

5.4 Configuration
- Routing: no runtime toggle. Path selection is determined solely by supports_responses_api(model).
- llm-level defaults:
  - store default False (we are stateless)
  - include default None; opt-in “reasoning.encrypted_content” for gpt-5, as an additional LLM attribute, enable_encrypted_reasoning.


6) Telemetry

- Dimensions:
  - llm_path: “responses” | “completions”
  - model, provider, latency_ms, success/failure
  - usage: input_tokens, output_tokens, total_tokens
- Note: we do not record presence or content of encrypted reasoning.
- Errors:
  - error_type (provider_error, rate_limit, invalid_request, etc.)
  - status_code if available


7) Implementation Plan

Milestone 1 (Non-stream parity)
- Add supports_responses_api(model)
- Implement llm.responses() (non-stream), mapping messages → instructions/input
- Map tools/tool_choice to Responses function tools
- Parse Response.output → SDK Message
- Tool calling loop with MessageToolCall for non-stream function calls
- Telemetry path + usage mapping
- Update Agent routing to call llm.responses() when supports_responses_api(model) is True
- Unit tests: parsing, routing, tool loop, telemetry
- Example: examples/26_responses_reasoning.py (simple text + optional reasoning include)

Milestone 2 (Streaming)
- llm.responses(..., stream=True) and event mapping
- Streaming function call loop (function_call_arguments.delta/done)
- Backpressure semantics: pause for tool outputs
- Tests + example

Milestone 3 (Reasoning support / encrypted pass-back)
- Add an opt-in to include=["reasoning.encrypted_content"]
- Store encrypted content for next turn when “stateless”
- Tests + example


8) Test Plan

Unit:
- supports_responses_api: gpt-5 → True; others False (unless configured)
- messages → instructions/input mapping:
  - Single system + single user → instructions + input[0]
  - Multiple system/dev → concatenation
  - Assistant previous content is included in input for proper context (or omitted per our current Agent policy if not used)
- tools: conversion from ToolBase → Responses tool schema
- tool_choice default: auto; no explicit parameter on responses() in v1
- output parsing: create LLMResponse with assistant message text
- usage mapping to MetricsSnapshot
- error surfaces (LiteLLM exceptions → our telemetry)

Integration (mock LiteLLM):
- Simple text turn: ensure route “responses”, parse output_text
- Function calling: ensure tool call mapping → tool execution → second turn works
- Telemetry asserts

Examples:
- examples/26_responses_reasoning.py: simple call with include=["reasoning.encrypted_content"] (prints if present)


9) Decisions

- Coding principle: "No dict soup!" — rely on LiteLLM types and typed SDK wrappers; avoid untyped dicts and defensive fallbacks.

- Default routing policy:
  - Auto by model (supports_responses_api) [Proposed default]

- Tool calls in v1:
  - Support non-stream tool calls if available from LiteLLM non-stream response (Proposed)

- Reasoning encrypted content:
  - A) enable_encrypted_reasoning: bool in LLM

- Telemetry fields: Should we record encrypted reasoning presence (boolean) in metrics.extra? No. (We will never log the content.)

- store default:
  - A) False (stateless; consistent with current agent loop) [Proposed]

- Built-in OpenAI tools:
  - No.

- Streaming priority:
  - A) Non-stream parity first [Proposed]


10) Risks and Mitigations

- IMPORTANT: function call representation is litellm types as returned. We rely on litellm, we don't test or fallback, do not add overly defensive behavior.

- Diverging semantics vs Completions:
  Mitigation: Keep single LLMResponse + unified tool loop; route selection is internal.


11) Appendix: Quick mapping (Completions vs Responses)

Inputs
- Completions (chat): messages=[system, user, …], tools, tool_choice, temperature/top_p, max_tokens
- Responses: instructions (system/dev), input (text list), tools, tool_choice, temperature/top_p, max_output_tokens, reasoning, include, parallel_tool_calls

Outputs
- Completions: choices[0].message.content (string), tool_calls (if any), usage
- Responses: output[] with items (message/output_text etc.), tool calls (items and/or streaming deltas), usage

Streaming (later)
- Chat: chunk stream with delta content
- Responses: rich event stream (response.created, response.output_text.delta, response.function_call_arguments.delta, …)


12) Deliverables checklist

- [ ] supports_responses_api(model)
- [ ] llm.responses() non-stream
- [ ] Tool mapping + MessageToolCall wrapper
IMPORTANT: look at this PR: https://github.com/All-Hands-AI/agent-sdk/pull/550
maybe merge it first, so that we have it and can use it for responses
- [ ] enable_encrypted_reasoning: bool in LLM
- [ ] Agent routing (auto via supports_responses_api)
- [ ] Telemetry updates
- [ ] Message/Visualizer updates (persist reasoning_summaries, reasoning_blocks, encrypted_reasoning; render plaintext only)
- [ ] Example 26_responses_reasoning.py
- [ ] Unit tests (parsing, routing, tool loop, telemetry)
- [ ] Streaming design documented (phase 2)

13) Tool result threading examples (Completions vs Responses)

Summary
- A tool result is the observation returned by a tool after a model-initiated function_call. The result must be threaded back to the model using the same identifier as the original call.
- Chat Completions:
  - Assistant function_call turn: an assistant message with tool_calls[] (each has id + function{name,arguments})
  - Tool result turn: a tool-role message with tool_call_id (matching the id from tool_calls[]) and name; content is the tool output string
- Responses:
  - Assistant function_call turn: an input item of type "function_call" (id/call_id must match and begin with "fc", arguments must be a JSON string)
  - Tool result turn: an input item of type "function_call_output" with call_id matching the prior function_call and output as a string

13.1 Chat Completions tool result example

```json
[
  { "role": "system", "content": "You are a helpful assistant." },
  { "role": "user", "content": "Please call foo with x=1." },

  {
    "role": "assistant",
    "content": "",
    "tool_calls": [
      {
        "id": "call_abc123",
        "type": "function",
        "function": { "name": "foo", "arguments": "{\"x\": 1}" }
      }
    ]
  },

  {
    "role": "tool",
    "tool_call_id": "call_abc123",
    "name": "foo",
    "content": "ok"
  }
]
```

Notes:
- The assistant function_call is represented via tool_calls[], each with id + function.
- The tool result is a single role="tool" message with tool_call_id + name and the output content.

13.2 Responses tool result example

```json
{
  "instructions": "You are a helpful assistant.",
  "input": [
    {
      "type": "message",
      "role": "user",
      "content": [{ "type": "input_text", "text": "Please call foo with x=1." }]
    },
    {
      "type": "function_call",
      "id": "fc_call_abc123",
      "call_id": "fc_call_abc123",
      "name": "foo",
      "arguments": "{\"x\": 1}"
    },
    {
      "type": "function_call_output",
      "call_id": "fc_call_abc123",
      "output": "ok"
    }
  ]
}
```

Notes:
- Assistant function_call is an input item with id/call_id prefixed "fc" and a JSON string arguments field.
- The tool result is a function_call_output item with a call_id that matches the previous function_call id (one-to-one threading).

---

def mock_responses_api_response(
    mock_response: str = "In a peaceful grove beneath a silver moon, a unicorn named Lumina discovered a hidden pool that reflected the stars. As she dipped her horn into the water, the pool began to shimmer, revealing a pathway to a magical realm of endless night skies. Filled with wonder, Lumina whispered a wish for all who dream to find their own hidden magic, and as she glanced back, her hoofprints sparkled like stardust.",
):
    return ResponsesAPIResponse(
        **{  # type: ignore
            "id": "resp_67ccd2bed1ec8190b14f964abc0542670bb6a6b452d3795b",
            "object": "response",
            "created_at": 1741476542,
            "status": "completed",
            "error": None,
            "incomplete_details": None,
            "instructions": None,
            "max_output_tokens": None,
            "model": "gpt-4.1-2025-04-14",
            "output": [
                {
                    "type": "message",
                    "id": "msg_67ccd2bf17f0819081ff3bb2cf6508e60bb6a6b452d3795b",
                    "status": "completed",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": mock_response,
                            "annotations": [],
                        }
                    ],
                }
            ],
            "parallel_tool_calls": True,
            "previous_response_id": None,
            "reasoning": {"effort": None, "summary": None},
            "store": True,
            "temperature": 1.0,
            "text": {"format": {"type": "text"}},
            "tool_choice": "auto",
            "tools": [],
            "top_p": 1.0,
            "truncation": "disabled",
            "usage": {
                "input_tokens": 36,
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens": 87,
                "output_tokens_details": {"reasoning_tokens": 0},
                "total_tokens": 123,
            },
            "user": None,
            "metadata": {},
        }
    )

---

Reference:

- litellm types: .venv/lib/python3.12/site-packages/litellm/types/llms/openai.py (class ResponsesAPIResponse has field reasoning: Optional[Reasoning] = None)
- litellm path: .venv/lib/python3.12/site-packages/litellm/responses/main.py mock_responses_api_response sets reasoning and the responses(...) path returns ResponsesAPIResponse with reasoning populated when present.

1. Does LiteLLM provide a wrapper for ResponseReasoningItem, or should we import from openai?

- LiteLLM does NOT expose a ResponseReasoningItem wrapper in its responses types. Inspect:
  - .venv/lib/python3.12/site-packages/litellm/types/responses/main.py
    - Provides GenericResponseOutputItem and OutputFunctionToolCall, but no reasoning item type.

- OpenAI SDK DOES define the typed reasoning item and includes it in the ResponseOutputItem union:

  - .venv/lib/python3.12/site-packages/openai/types/responses/response_output_item.py
    - ResponseOutputItem includes ResponseReasoningItem as one of the discriminator variants.

  - .venv/lib/python3.12/site-packages/openai/types/responses/response_reasoning_item.py
    - class ResponseReasoningItem with fields:
      - id: str
      - type: Literal["reasoning"]
      - summary: List[Summary] (Summary has text: str, type: "summary_text")
      - content: Optional[List[Content]] (Content has text: str, type: "reasoning_text")
      - encrypted_content: Optional[str]
      - status: Optional[Literal["in_progress","completed","incomplete"]]

- How LiteLLM returns output[]:
  - .venv/lib/python3.12/site-packages/litellm/types/llms/openai.py (class ResponsesAPIResponse)
    - Field output is a union that can contain either:
      - OpenAI SDK typed ResponseOutputItem (which includes ResponseReasoningItem), or
      - LiteLLM’s GenericResponseOutputItem/OutputFunctionToolCall

- Therefore, the correct approach is:
  - Prefer OpenAI types for typed reasoning item detection: import ResponseOutputMessage and ResponseReasoningItem from openai.types.
  - Keep LiteLLM GenericResponseOutputItem for message text fallback, and OutputFunctionToolCall for tools.

2. Where does LiteLLM set/use reasoning?

- INPUT and INPUT-like: top-level “reasoning” (effort/summary at the response level) is on ResponsesAPIResponse.reasoning (separate from output[] items):
  - .venv/lib/python3.12/site-packages/litellm/types/llms/openai.py (field reasoning)
  - Example mock in .venv/lib/python3.12/site-packages/litellm/responses/main.py (mock_responses_api_response sets reasoning; responses() returns a ResponsesAPIResponse)

- OUTPUT: Output[] typed reasoning items (type="reasoning") are defined in OpenAI SDK and can be delivered by LiteLLM when it passes through the OpenAI typed ResponseOutputItem union.

3. Where LiteLLM sends reasoning and exact local files:

  - Top-level reasoning (effort/summary) is a separate Pydantic field on the response object:

    - File: .venv/lib/python3.12/site-packages/litellm/types/llms/openai.py → class ResponsesAPIResponse has field reasoning: Optional[Reasoning]
    - File: .venv/lib/python3.12/site-packages/litellm/responses/main.py → responses(...) builds and returns ResponsesAPIResponse; mock_responses_api_response sets reasoning for demonstration

  - Output[] typed items (including ResponseReasoningItem) come through OpenAI SDK’s ResponseOutputItem union:
    - File: .venv/lib/python3.12/site-packages/openai/types/responses/response_output_item.py includes ResponseReasoningItem in the union

---

