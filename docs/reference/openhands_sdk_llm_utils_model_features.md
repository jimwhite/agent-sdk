# openhands.sdk.llm.utils.model_features

## Classes

### ModelFeatures

ModelFeatures(supports_function_calling: bool, supports_reasoning_effort: bool, supports_prompt_cache: bool, supports_stop_words: bool)

## Functions

### get_features(model: str) -> openhands.sdk.llm.utils.model_features.ModelFeatures

### model_matches(model: str, patterns: list[str]) -> bool

Return True if the model matches any of the glob patterns.

If a pattern contains a '/', it is treated as provider-qualified and matched
against the full, lowercased model string (including provider prefix).
Otherwise, it is matched against the normalized basename.

### normalize_model_name(model: str) -> str

Normalize a model string to a canonical, comparable name.

Strategy:
- Trim whitespace
- Lowercase
- If there is a '/', keep only the basename after the last '/'
  (handles prefixes like openrouter/, litellm_proxy/, anthropic/, etc.)
  and treat ':' inside that basename as an Ollama-style variant tag to be removed
- There is no provider:model form; providers, when present, use 'provider/model'
- Drop a trailing "-gguf" suffix if present
- If basename starts with a known vendor prefix followed by '.', drop that prefix
  (e.g., 'anthropic.claude-*' -> 'claude-*')

