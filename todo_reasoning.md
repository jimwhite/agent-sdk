TODO: Responses API reasoning in stateless mode

Scope
- Applies only to OpenAI models that support the Responses API
- Our current agent runs stateless (we do not use previous_response_id)

Current behavior (stateless)
- We do NOT send prior reasoning back to the model.
- We only resend prior conversation context via:
  - Plain text messages (user/system/developer/assistant where applicable)
  - Assistant tool_calls as Responses items of type function_call
  - Tool outputs as Responses items of type function_call_output
- The model generates fresh reasoning each call.

Do we need to resend reasoning?
- Not required. The model can re-reason every turn.
- If we want state fidelity comparable to server-managed mode, we can include
  prior reasoning items in our next stateless request, but this is optional.

What it takes to include reasoning (stateless)
1) Capture reasoning items from Responses output
   - litellm.responses returns output items; reasoning is one of those types.
   - Today we convert Responses output into a Chat Completions-shaped response
     and expose only a flattened reasoning_content string on the assistant
     message. That is not sufficient to reconstruct a proper Responses
     input item.

2) Persist reasoning items in conversation history
   - Store each turn’s raw Responses items (or at least the reasoning item)
     alongside the turn. Options:
     - Attach provider-specific metadata to the assistant turn, OR
     - Maintain a parallel list keyed by turn.

3) Re-emit reasoning items on follow-up stateless calls
   - Update _messages_to_responses_items to also append stored reasoning items
     (type: "reasoning") from previous turns, before adding new input for the
     current turn, in chronological order.
   - Populate the fields per the OpenAI SDK type
     ResponseReasoningItemParam (id, summary, content/status if present), using
     the values captured from the prior response.

4) Considerations / trade-offs
- Larger request payloads and higher token cost.
- Potential exposure of internal reasoning summaries beyond what is strictly
  required.
- More complex state: the agent must persist and serialize reasoning items to
  include them on subsequent turns (surviving restarts if needed).
- If later we adopt server-managed (stateful) mode via previous_response_id,
  we can stop sending prior reasoning because the server will manage it.

Summary
- We are stateless and do not resend reasoning today.
- Resending reasoning is optional. To enable it, retain the raw Responses
  reasoning items per turn and extend _messages_to_responses_items to inject
  those items into the next request for OpenAI Responses-supported models.

---

uvx --python 3.12 --from git+https://github.com/All-Hands-AI/OpenHands@v1#subdirectory=openhands-cli openhands-cli

---
