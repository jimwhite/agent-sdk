from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define

from ..models.llm_reasoning_effort_type_0 import LLMReasoningEffortType0, check_llm_reasoning_effort_type_0
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.llm_safety_settings_type_0_item import LLMSafetySettingsType0Item


T = TypeVar("T", bound="LLM")


@_attrs_define
class LLM:
    """Refactored LLM: simple `completion()`, centralized Telemetry, tiny helpers.

    Attributes:
        model (Union[Unset, str]): Model name. Default: 'claude-sonnet-4-20250514'.
        api_key (Union[None, Unset, str]): API key.
        base_url (Union[None, Unset, str]): Custom base URL.
        api_version (Union[None, Unset, str]): API version (e.g., Azure).
        aws_access_key_id (Union[None, Unset, str]):
        aws_secret_access_key (Union[None, Unset, str]):
        aws_region_name (Union[None, Unset, str]):
        openrouter_site_url (Union[Unset, str]):  Default: 'https://docs.all-hands.dev/'.
        openrouter_app_name (Union[Unset, str]):  Default: 'OpenHands'.
        num_retries (Union[Unset, int]):  Default: 5.
        retry_multiplier (Union[Unset, float]):  Default: 8.0.
        retry_min_wait (Union[Unset, int]):  Default: 8.
        retry_max_wait (Union[Unset, int]):  Default: 64.
        timeout (Union[None, Unset, int]): HTTP timeout (s).
        max_message_chars (Union[Unset, int]): Approx max chars in each event/content sent to the LLM. Default: 30000.
        temperature (Union[None, Unset, float]):  Default: 0.0.
        top_p (Union[None, Unset, float]):  Default: 1.0.
        top_k (Union[None, Unset, float]):
        custom_llm_provider (Union[None, Unset, str]):
        max_input_tokens (Union[None, Unset, int]): The maximum number of input tokens. Note that this is currently
            unused, and the value at runtime is actually the total tokens in OpenAI (e.g. 128,000 tokens for GPT-4).
        max_output_tokens (Union[None, Unset, int]): The maximum number of output tokens. This is sent to the LLM.
        input_cost_per_token (Union[None, Unset, float]): The cost per input token. This will available in logs for
            user.
        output_cost_per_token (Union[None, Unset, float]): The cost per output token. This will available in logs for
            user.
        ollama_base_url (Union[None, Unset, str]):
        drop_params (Union[Unset, bool]):  Default: True.
        modify_params (Union[Unset, bool]): Modify params allows litellm to do transformations like adding a default
            message, when a message is empty. Default: True.
        disable_vision (Union[None, Unset, bool]): If model is vision capable, this option allows to disable image
            processing (useful for cost reduction).
        disable_stop_word (Union[None, Unset, bool]): Disable using of stop word. Default: False.
        caching_prompt (Union[Unset, bool]): Enable caching of prompts. Default: True.
        log_completions (Union[Unset, bool]): Enable logging of completions. Default: False.
        log_completions_folder (Union[Unset, str]): The folder to log LLM completions to. Required if log_completions is
            True. Default: 'logs/completions'.
        custom_tokenizer (Union[None, Unset, str]): A custom tokenizer to use for token counting.
        native_tool_calling (Union[None, Unset, bool]): Whether to use native tool calling if supported by the model.
            Can be True, False, or not set.
        reasoning_effort (Union[LLMReasoningEffortType0, None, Unset]): The effort to put into reasoning. This is a
            string that can be one of 'low', 'medium', 'high', or 'none'. Can apply to all reasoning models.
        seed (Union[None, Unset, int]): The seed to use for random number generation.
        safety_settings (Union[None, Unset, list['LLMSafetySettingsType0Item']]): Safety settings for models that
            support them (like Mistral AI and Gemini)
        service_id (Union[Unset, str]): Unique identifier for LLM. Typically used by LLM registry. Default: 'default'.
        override_on_serialize (Union[Unset, list[str]]):
    """

    model: Union[Unset, str] = "claude-sonnet-4-20250514"
    api_key: Union[None, Unset, str] = UNSET
    base_url: Union[None, Unset, str] = UNSET
    api_version: Union[None, Unset, str] = UNSET
    aws_access_key_id: Union[None, Unset, str] = UNSET
    aws_secret_access_key: Union[None, Unset, str] = UNSET
    aws_region_name: Union[None, Unset, str] = UNSET
    openrouter_site_url: Union[Unset, str] = "https://docs.all-hands.dev/"
    openrouter_app_name: Union[Unset, str] = "OpenHands"
    num_retries: Union[Unset, int] = 5
    retry_multiplier: Union[Unset, float] = 8.0
    retry_min_wait: Union[Unset, int] = 8
    retry_max_wait: Union[Unset, int] = 64
    timeout: Union[None, Unset, int] = UNSET
    max_message_chars: Union[Unset, int] = 30000
    temperature: Union[None, Unset, float] = 0.0
    top_p: Union[None, Unset, float] = 1.0
    top_k: Union[None, Unset, float] = UNSET
    custom_llm_provider: Union[None, Unset, str] = UNSET
    max_input_tokens: Union[None, Unset, int] = UNSET
    max_output_tokens: Union[None, Unset, int] = UNSET
    input_cost_per_token: Union[None, Unset, float] = UNSET
    output_cost_per_token: Union[None, Unset, float] = UNSET
    ollama_base_url: Union[None, Unset, str] = UNSET
    drop_params: Union[Unset, bool] = True
    modify_params: Union[Unset, bool] = True
    disable_vision: Union[None, Unset, bool] = UNSET
    disable_stop_word: Union[None, Unset, bool] = False
    caching_prompt: Union[Unset, bool] = True
    log_completions: Union[Unset, bool] = False
    log_completions_folder: Union[Unset, str] = "logs/completions"
    custom_tokenizer: Union[None, Unset, str] = UNSET
    native_tool_calling: Union[None, Unset, bool] = UNSET
    reasoning_effort: Union[LLMReasoningEffortType0, None, Unset] = UNSET
    seed: Union[None, Unset, int] = UNSET
    safety_settings: Union[None, Unset, list["LLMSafetySettingsType0Item"]] = UNSET
    service_id: Union[Unset, str] = "default"
    override_on_serialize: Union[Unset, list[str]] = UNSET

    def to_dict(self) -> dict[str, Any]:
        model = self.model

        api_key: Union[None, Unset, str]
        if isinstance(self.api_key, Unset):
            api_key = UNSET
        else:
            api_key = self.api_key

        base_url: Union[None, Unset, str]
        if isinstance(self.base_url, Unset):
            base_url = UNSET
        else:
            base_url = self.base_url

        api_version: Union[None, Unset, str]
        if isinstance(self.api_version, Unset):
            api_version = UNSET
        else:
            api_version = self.api_version

        aws_access_key_id: Union[None, Unset, str]
        if isinstance(self.aws_access_key_id, Unset):
            aws_access_key_id = UNSET
        else:
            aws_access_key_id = self.aws_access_key_id

        aws_secret_access_key: Union[None, Unset, str]
        if isinstance(self.aws_secret_access_key, Unset):
            aws_secret_access_key = UNSET
        else:
            aws_secret_access_key = self.aws_secret_access_key

        aws_region_name: Union[None, Unset, str]
        if isinstance(self.aws_region_name, Unset):
            aws_region_name = UNSET
        else:
            aws_region_name = self.aws_region_name

        openrouter_site_url = self.openrouter_site_url

        openrouter_app_name = self.openrouter_app_name

        num_retries = self.num_retries

        retry_multiplier = self.retry_multiplier

        retry_min_wait = self.retry_min_wait

        retry_max_wait = self.retry_max_wait

        timeout: Union[None, Unset, int]
        if isinstance(self.timeout, Unset):
            timeout = UNSET
        else:
            timeout = self.timeout

        max_message_chars = self.max_message_chars

        temperature: Union[None, Unset, float]
        if isinstance(self.temperature, Unset):
            temperature = UNSET
        else:
            temperature = self.temperature

        top_p: Union[None, Unset, float]
        if isinstance(self.top_p, Unset):
            top_p = UNSET
        else:
            top_p = self.top_p

        top_k: Union[None, Unset, float]
        if isinstance(self.top_k, Unset):
            top_k = UNSET
        else:
            top_k = self.top_k

        custom_llm_provider: Union[None, Unset, str]
        if isinstance(self.custom_llm_provider, Unset):
            custom_llm_provider = UNSET
        else:
            custom_llm_provider = self.custom_llm_provider

        max_input_tokens: Union[None, Unset, int]
        if isinstance(self.max_input_tokens, Unset):
            max_input_tokens = UNSET
        else:
            max_input_tokens = self.max_input_tokens

        max_output_tokens: Union[None, Unset, int]
        if isinstance(self.max_output_tokens, Unset):
            max_output_tokens = UNSET
        else:
            max_output_tokens = self.max_output_tokens

        input_cost_per_token: Union[None, Unset, float]
        if isinstance(self.input_cost_per_token, Unset):
            input_cost_per_token = UNSET
        else:
            input_cost_per_token = self.input_cost_per_token

        output_cost_per_token: Union[None, Unset, float]
        if isinstance(self.output_cost_per_token, Unset):
            output_cost_per_token = UNSET
        else:
            output_cost_per_token = self.output_cost_per_token

        ollama_base_url: Union[None, Unset, str]
        if isinstance(self.ollama_base_url, Unset):
            ollama_base_url = UNSET
        else:
            ollama_base_url = self.ollama_base_url

        drop_params = self.drop_params

        modify_params = self.modify_params

        disable_vision: Union[None, Unset, bool]
        if isinstance(self.disable_vision, Unset):
            disable_vision = UNSET
        else:
            disable_vision = self.disable_vision

        disable_stop_word: Union[None, Unset, bool]
        if isinstance(self.disable_stop_word, Unset):
            disable_stop_word = UNSET
        else:
            disable_stop_word = self.disable_stop_word

        caching_prompt = self.caching_prompt

        log_completions = self.log_completions

        log_completions_folder = self.log_completions_folder

        custom_tokenizer: Union[None, Unset, str]
        if isinstance(self.custom_tokenizer, Unset):
            custom_tokenizer = UNSET
        else:
            custom_tokenizer = self.custom_tokenizer

        native_tool_calling: Union[None, Unset, bool]
        if isinstance(self.native_tool_calling, Unset):
            native_tool_calling = UNSET
        else:
            native_tool_calling = self.native_tool_calling

        reasoning_effort: Union[None, Unset, str]
        if isinstance(self.reasoning_effort, Unset):
            reasoning_effort = UNSET
        elif isinstance(self.reasoning_effort, str):
            reasoning_effort = self.reasoning_effort
        else:
            reasoning_effort = self.reasoning_effort

        seed: Union[None, Unset, int]
        if isinstance(self.seed, Unset):
            seed = UNSET
        else:
            seed = self.seed

        safety_settings: Union[None, Unset, list[dict[str, Any]]]
        if isinstance(self.safety_settings, Unset):
            safety_settings = UNSET
        elif isinstance(self.safety_settings, list):
            safety_settings = []
            for safety_settings_type_0_item_data in self.safety_settings:
                safety_settings_type_0_item = safety_settings_type_0_item_data.to_dict()
                safety_settings.append(safety_settings_type_0_item)

        else:
            safety_settings = self.safety_settings

        service_id = self.service_id

        override_on_serialize: Union[Unset, list[str]] = UNSET
        if not isinstance(self.override_on_serialize, Unset):
            override_on_serialize = self.override_on_serialize

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if model is not UNSET:
            field_dict["model"] = model
        if api_key is not UNSET:
            field_dict["api_key"] = api_key
        if base_url is not UNSET:
            field_dict["base_url"] = base_url
        if api_version is not UNSET:
            field_dict["api_version"] = api_version
        if aws_access_key_id is not UNSET:
            field_dict["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key is not UNSET:
            field_dict["aws_secret_access_key"] = aws_secret_access_key
        if aws_region_name is not UNSET:
            field_dict["aws_region_name"] = aws_region_name
        if openrouter_site_url is not UNSET:
            field_dict["openrouter_site_url"] = openrouter_site_url
        if openrouter_app_name is not UNSET:
            field_dict["openrouter_app_name"] = openrouter_app_name
        if num_retries is not UNSET:
            field_dict["num_retries"] = num_retries
        if retry_multiplier is not UNSET:
            field_dict["retry_multiplier"] = retry_multiplier
        if retry_min_wait is not UNSET:
            field_dict["retry_min_wait"] = retry_min_wait
        if retry_max_wait is not UNSET:
            field_dict["retry_max_wait"] = retry_max_wait
        if timeout is not UNSET:
            field_dict["timeout"] = timeout
        if max_message_chars is not UNSET:
            field_dict["max_message_chars"] = max_message_chars
        if temperature is not UNSET:
            field_dict["temperature"] = temperature
        if top_p is not UNSET:
            field_dict["top_p"] = top_p
        if top_k is not UNSET:
            field_dict["top_k"] = top_k
        if custom_llm_provider is not UNSET:
            field_dict["custom_llm_provider"] = custom_llm_provider
        if max_input_tokens is not UNSET:
            field_dict["max_input_tokens"] = max_input_tokens
        if max_output_tokens is not UNSET:
            field_dict["max_output_tokens"] = max_output_tokens
        if input_cost_per_token is not UNSET:
            field_dict["input_cost_per_token"] = input_cost_per_token
        if output_cost_per_token is not UNSET:
            field_dict["output_cost_per_token"] = output_cost_per_token
        if ollama_base_url is not UNSET:
            field_dict["ollama_base_url"] = ollama_base_url
        if drop_params is not UNSET:
            field_dict["drop_params"] = drop_params
        if modify_params is not UNSET:
            field_dict["modify_params"] = modify_params
        if disable_vision is not UNSET:
            field_dict["disable_vision"] = disable_vision
        if disable_stop_word is not UNSET:
            field_dict["disable_stop_word"] = disable_stop_word
        if caching_prompt is not UNSET:
            field_dict["caching_prompt"] = caching_prompt
        if log_completions is not UNSET:
            field_dict["log_completions"] = log_completions
        if log_completions_folder is not UNSET:
            field_dict["log_completions_folder"] = log_completions_folder
        if custom_tokenizer is not UNSET:
            field_dict["custom_tokenizer"] = custom_tokenizer
        if native_tool_calling is not UNSET:
            field_dict["native_tool_calling"] = native_tool_calling
        if reasoning_effort is not UNSET:
            field_dict["reasoning_effort"] = reasoning_effort
        if seed is not UNSET:
            field_dict["seed"] = seed
        if safety_settings is not UNSET:
            field_dict["safety_settings"] = safety_settings
        if service_id is not UNSET:
            field_dict["service_id"] = service_id
        if override_on_serialize is not UNSET:
            field_dict["OVERRIDE_ON_SERIALIZE"] = override_on_serialize

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.llm_safety_settings_type_0_item import LLMSafetySettingsType0Item

        d = dict(src_dict)
        model = d.pop("model", UNSET)

        def _parse_api_key(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        api_key = _parse_api_key(d.pop("api_key", UNSET))

        def _parse_base_url(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        base_url = _parse_base_url(d.pop("base_url", UNSET))

        def _parse_api_version(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        api_version = _parse_api_version(d.pop("api_version", UNSET))

        def _parse_aws_access_key_id(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        aws_access_key_id = _parse_aws_access_key_id(d.pop("aws_access_key_id", UNSET))

        def _parse_aws_secret_access_key(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        aws_secret_access_key = _parse_aws_secret_access_key(d.pop("aws_secret_access_key", UNSET))

        def _parse_aws_region_name(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        aws_region_name = _parse_aws_region_name(d.pop("aws_region_name", UNSET))

        openrouter_site_url = d.pop("openrouter_site_url", UNSET)

        openrouter_app_name = d.pop("openrouter_app_name", UNSET)

        num_retries = d.pop("num_retries", UNSET)

        retry_multiplier = d.pop("retry_multiplier", UNSET)

        retry_min_wait = d.pop("retry_min_wait", UNSET)

        retry_max_wait = d.pop("retry_max_wait", UNSET)

        def _parse_timeout(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        timeout = _parse_timeout(d.pop("timeout", UNSET))

        max_message_chars = d.pop("max_message_chars", UNSET)

        def _parse_temperature(data: object) -> Union[None, Unset, float]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, float], data)

        temperature = _parse_temperature(d.pop("temperature", UNSET))

        def _parse_top_p(data: object) -> Union[None, Unset, float]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, float], data)

        top_p = _parse_top_p(d.pop("top_p", UNSET))

        def _parse_top_k(data: object) -> Union[None, Unset, float]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, float], data)

        top_k = _parse_top_k(d.pop("top_k", UNSET))

        def _parse_custom_llm_provider(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        custom_llm_provider = _parse_custom_llm_provider(d.pop("custom_llm_provider", UNSET))

        def _parse_max_input_tokens(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        max_input_tokens = _parse_max_input_tokens(d.pop("max_input_tokens", UNSET))

        def _parse_max_output_tokens(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        max_output_tokens = _parse_max_output_tokens(d.pop("max_output_tokens", UNSET))

        def _parse_input_cost_per_token(data: object) -> Union[None, Unset, float]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, float], data)

        input_cost_per_token = _parse_input_cost_per_token(d.pop("input_cost_per_token", UNSET))

        def _parse_output_cost_per_token(data: object) -> Union[None, Unset, float]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, float], data)

        output_cost_per_token = _parse_output_cost_per_token(d.pop("output_cost_per_token", UNSET))

        def _parse_ollama_base_url(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        ollama_base_url = _parse_ollama_base_url(d.pop("ollama_base_url", UNSET))

        drop_params = d.pop("drop_params", UNSET)

        modify_params = d.pop("modify_params", UNSET)

        def _parse_disable_vision(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        disable_vision = _parse_disable_vision(d.pop("disable_vision", UNSET))

        def _parse_disable_stop_word(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        disable_stop_word = _parse_disable_stop_word(d.pop("disable_stop_word", UNSET))

        caching_prompt = d.pop("caching_prompt", UNSET)

        log_completions = d.pop("log_completions", UNSET)

        log_completions_folder = d.pop("log_completions_folder", UNSET)

        def _parse_custom_tokenizer(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        custom_tokenizer = _parse_custom_tokenizer(d.pop("custom_tokenizer", UNSET))

        def _parse_native_tool_calling(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        native_tool_calling = _parse_native_tool_calling(d.pop("native_tool_calling", UNSET))

        def _parse_reasoning_effort(data: object) -> Union[LLMReasoningEffortType0, None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                reasoning_effort_type_0 = check_llm_reasoning_effort_type_0(data)

                return reasoning_effort_type_0
            except:  # noqa: E722
                pass
            return cast(Union[LLMReasoningEffortType0, None, Unset], data)

        reasoning_effort = _parse_reasoning_effort(d.pop("reasoning_effort", UNSET))

        def _parse_seed(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        seed = _parse_seed(d.pop("seed", UNSET))

        def _parse_safety_settings(data: object) -> Union[None, Unset, list["LLMSafetySettingsType0Item"]]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                safety_settings_type_0 = []
                _safety_settings_type_0 = data
                for safety_settings_type_0_item_data in _safety_settings_type_0:
                    safety_settings_type_0_item = LLMSafetySettingsType0Item.from_dict(safety_settings_type_0_item_data)

                    safety_settings_type_0.append(safety_settings_type_0_item)

                return safety_settings_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, list["LLMSafetySettingsType0Item"]], data)

        safety_settings = _parse_safety_settings(d.pop("safety_settings", UNSET))

        service_id = d.pop("service_id", UNSET)

        override_on_serialize = cast(list[str], d.pop("OVERRIDE_ON_SERIALIZE", UNSET))

        llm = cls(
            model=model,
            api_key=api_key,
            base_url=base_url,
            api_version=api_version,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_region_name=aws_region_name,
            openrouter_site_url=openrouter_site_url,
            openrouter_app_name=openrouter_app_name,
            num_retries=num_retries,
            retry_multiplier=retry_multiplier,
            retry_min_wait=retry_min_wait,
            retry_max_wait=retry_max_wait,
            timeout=timeout,
            max_message_chars=max_message_chars,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            custom_llm_provider=custom_llm_provider,
            max_input_tokens=max_input_tokens,
            max_output_tokens=max_output_tokens,
            input_cost_per_token=input_cost_per_token,
            output_cost_per_token=output_cost_per_token,
            ollama_base_url=ollama_base_url,
            drop_params=drop_params,
            modify_params=modify_params,
            disable_vision=disable_vision,
            disable_stop_word=disable_stop_word,
            caching_prompt=caching_prompt,
            log_completions=log_completions,
            log_completions_folder=log_completions_folder,
            custom_tokenizer=custom_tokenizer,
            native_tool_calling=native_tool_calling,
            reasoning_effort=reasoning_effort,
            seed=seed,
            safety_settings=safety_settings,
            service_id=service_id,
            override_on_serialize=override_on_serialize,
        )

        return llm
