# openhands.sdk.llm.utils.retry_mixin

## Classes

### RetryMixin

Mixin class for retry logic.

#### Functions

##### log_retry_attempt(self, retry_state: tenacity.RetryCallState) -> None

Log retry attempts.

##### retry_decorator(self, num_retries: int = 5, retry_exceptions: tuple[type[BaseException], ...] = (<class 'openhands.sdk.llm.exceptions.LLMNoResponseError'>,), retry_min_wait: int = 8, retry_max_wait: int = 64, retry_multiplier: float = 2.0, retry_listener: Optional[Callable[[int, int], NoneType]] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]

Create a LLM retry decorator with customizable parameters.
This is used for 429 errors, and a few other exceptions in LLM classes.

