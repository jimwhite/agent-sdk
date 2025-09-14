
/Users/enyst/repos/agent-sdk/.worktrees/responses/openhands/sdk/llm/llm.py
  /Users/enyst/repos/agent-sdk/.worktrees/responses/openhands/sdk/llm/llm.py:367:60 - error: Argument of type "list[ChatCompletionToolParam] | list[Tool[Unknown, Unknown]] | None" cannot be assigned to parameter "tools" of type "Sequence[dict[str, Any]] | None" in function "responses"
    Type "list[ChatCompletionToolParam] | list[Tool[Unknown, Unknown]] | None" is not assignable to type "Sequence[dict[str, Any]] | None"
      Type "list[ChatCompletionToolParam]" is not assignable to type "Sequence[dict[str, Any]] | None"
        "list[ChatCompletionToolParam]" is not assignable to "Sequence[dict[str, Any]]"
          Type parameter "_T_co@Sequence" is covariant, but "ChatCompletionToolParam" is not a subtype of "dict[str, Any]"
            "ChatCompletionToolParam" is not assignable to "dict[str, Any]"
        "list[ChatCompletionToolParam]" is not assignable to "None" (reportArgumentType)
  /Users/enyst/repos/agent-sdk/.worktrees/responses/openhands/sdk/llm/llm.py:384:19 - error: Argument of type "list[ChatCompletionToolParam] | list[dict[str, Any]] | list[Tool[Unknown, Unknown]]" cannot be assigned to parameter "tools" of type "list[dict[str, Any]] | None" in function "_unified_request"
    Type "list[ChatCompletionToolParam] | list[dict[str, Any]] | list[Tool[Unknown, Unknown]]" is not assignable to type "list[dict[str, Any]] | None"
      Type "list[ChatCompletionToolParam]" is not assignable to type "list[dict[str, Any]] | None"
        "list[ChatCompletionToolParam]" is not assignable to "list[dict[str, Any]]"
          Type parameter "_T@list" is invariant, but "ChatCompletionToolParam" is not the same as "dict[str, Any]"
          Consider switching from "list" to "Sequence" which is covariant
        "list[ChatCompletionToolParam]" is not assignable to "None" (reportArgumentType)
  /Users/enyst/repos/agent-sdk/.worktrees/responses/openhands/sdk/llm/llm.py:423:24 - error: Cannot access attribute "to_responses_tool" for class "<subclass of dict[str, Any] and Tool>"
    Attribute "to_responses_tool" is unknown (reportAttributeAccessIssue)
  /Users/enyst/repos/agent-sdk/.worktrees/responses/openhands/sdk/llm/llm.py:428:19 - error: Argument of type "list[Unknown | dict[str, Any]] | list[dict[str, Any]] | Sequence[dict[str, Any]]" cannot be assigned to parameter "tools" of type "list[dict[str, Any]] | None" in function "_unified_request"
    Type "list[Unknown | dict[str, Any]] | list[dict[str, Any]] | Sequence[dict[str, Any]]" is not assignable to type "list[dict[str, Any]] | None"
      Type "Sequence[dict[str, Any]]" is not assignable to type "list[dict[str, Any]] | None"
        "Sequence[dict[str, Any]]" is not assignable to "list[dict[str, Any]]"
        "Sequence[dict[str, Any]]" is not assignable to "None" (reportArgumentType)
  /Users/enyst/repos/agent-sdk/.worktrees/responses/openhands/sdk/llm/llm.py:501:54 - error: Argument of type "list[dict[str, Any]] | None" cannot be assigned to parameter "tools" of type "list[ChatCompletionToolParam] | None" in function "should_mock_tool_calls"
    Type "list[dict[str, Any]] | None" is not assignable to type "list[ChatCompletionToolParam] | None"
      Type "list[dict[str, Any]]" is not assignable to type "list[ChatCompletionToolParam] | None"
        "list[dict[str, Any]]" is not assignable to "list[ChatCompletionToolParam]"
          Type parameter "_T@list" is invariant, but "dict[str, Any]" is not the same as "ChatCompletionToolParam"
          Consider switching from "list" to "Sequence" which is covariant
        "list[dict[str, Any]]" is not assignable to "None" (reportArgumentType)
  /Users/enyst/repos/agent-sdk/.worktrees/responses/openhands/sdk/llm/llm.py:507:61 - error: Argument of type "list[dict[str, Any]] | None" cannot be assigned to parameter "messages" of type "list[dict[Unknown, Unknown]]" in function "pre_request_prompt_mock"
    Type "list[dict[str, Any]] | None" is not assignable to type "list[dict[Unknown, Unknown]]"
      "None" is not assignable to "list[dict[Unknown, Unknown]]" (reportArgumentType)
  /Users/enyst/repos/agent-sdk/.worktrees/responses/openhands/sdk/llm/llm.py:507:71 - error: Argument of type "list[dict[str, Any]] | list[ChatCompletionToolParam]" cannot be assigned to parameter "tools" of type "list[ChatCompletionToolParam]" in function "pre_request_prompt_mock"
    Type "list[dict[str, Any]] | list[ChatCompletionToolParam]" is not assignable to type "list[ChatCompletionToolParam]"
      "list[dict[str, Any]]" is not assignable to "list[ChatCompletionToolParam]"
        Type parameter "_T@list" is invariant, but "dict[str, Any]" is not the same as "ChatCompletionToolParam"
        Consider switching from "list" to "Sequence" which is covariant (reportArgumentType)
  /Users/enyst/repos/agent-sdk/.worktrees/responses/openhands/sdk/llm/llm.py:531:23 - error: Argument of type "list[dict[str, Any]] | None" cannot be assigned to parameter "tools" of type "list[ChatCompletionToolParam]" in function "__init__"
    Type "list[dict[str, Any]] | None" is not assignable to type "list[ChatCompletionToolParam]"
      "list[dict[str, Any]]" is not assignable to "list[ChatCompletionToolParam]"
        Type parameter "_T@list" is invariant, but "dict[str, Any]" is not the same as "ChatCompletionToolParam"
        Consider switching from "list" to "Sequence" which is covariant (reportArgumentType)
  /Users/enyst/repos/agent-sdk/.worktrees/responses/openhands/sdk/llm/llm.py:540:23 - error: Argument of type "list[dict[str, Any]] | None" cannot be assigned to parameter "tools" of type "list[ChatCompletionToolParam]" in function "__init__"
    Type "list[dict[str, Any]] | None" is not assignable to type "list[ChatCompletionToolParam]"
      "list[dict[str, Any]]" is not assignable to "list[ChatCompletionToolParam]"
        Type parameter "_T@list" is invariant, but "dict[str, Any]" is not the same as "ChatCompletionToolParam"
        Consider switching from "list" to "Sequence" which is covariant (reportArgumentType)
  /Users/enyst/repos/agent-sdk/.worktrees/responses/openhands/sdk/llm/llm.py:659:59 - error: Argument of type "ResponsesAPIResponse | CoroutineType[Any, Any, ResponsesAPIResponse | BaseResponsesAPIStreamingIterator] | BaseResponsesAPIStreamingIterator | Coroutine[Any, Any, ResponsesAPIResponse | BaseResponsesAPIStreamingIterator]" cannot be assigned to parameter "responses_result" of type "ResponsesAPIResponse" in function "responses_to_completion_format"
    Type "ResponsesAPIResponse | CoroutineType[Any, Any, ResponsesAPIResponse | BaseResponsesAPIStreamingIterator] | BaseResponsesAPIStreamingIterator | Coroutine[Any, Any, ResponsesAPIResponse | BaseResponsesAPIStreamingIterator]" is not assignable to type "ResponsesAPIResponse"
      "BaseResponsesAPIStreamingIterator" is not assignable to "ResponsesAPIResponse" (reportArgumentType)
10 errors, 0 warnings, 0 informations
