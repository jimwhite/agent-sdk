# openhands.sdk.llm.exceptions

## Classes

### FunctionCallConversionError

Exception raised when FunctionCallingConverter failed to convert a non-function
call message to a function call message.

This typically happens when there's a malformed message (e.g., missing
<function=...> tags). But not due to LLM output.

### FunctionCallNotExistsError

Exception raised when an LLM call a tool that is not registered.

### FunctionCallValidationError

Exception raised when FunctionCallingConverter failed to validate a function
call message.

This typically happens when the LLM outputs unrecognized function call /
parameter names / values.

### LLMContextWindowExceedError

Base class for all LLM-related exceptions.

### LLMError

Base class for all LLM-related exceptions.

### LLMMalformedActionError

Exception raised when the LLM response is malformed or does not conform to the expected format.

### LLMNoActionError

Exception raised when the LLM response does not include an action.

### LLMNoResponseError

Exception raised when the LLM does not return a response, typically seen in
Gemini models.

This exception should be retried
Typically, after retry with a non-zero temperature, the LLM will return a response

### LLMResponseError

Exception raised when the LLM response does not include an action or the action is not of the expected type.

### OperationCancelled

Exception raised when an operation is cancelled (e.g. by a keyboard interrupt).

### UserCancelledError

Common base class for all non-exit exceptions.

