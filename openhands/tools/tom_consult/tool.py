"""Tom consultation tool definition."""

from collections.abc import Sequence

from openhands.sdk.io import LocalFileStore
from openhands.sdk.tool import ToolDefinition
from openhands.tools.tom_consult.action import ConsultTomAction
from openhands.tools.tom_consult.executor import TomConsultExecutor
from openhands.tools.tom_consult.observation import ConsultTomObservation


_DESCRIPTION = """Consult Tom agent for guidance when you need help \
understanding user intent or task requirements.

This tool allows you to consult Tom agent for personalized guidance \
based on user modeling. Use this when:
- User instructions are vague or unclear
- You need help understanding what the user actually wants
- You want guidance on the best approach for the current task
- You have your own question for Tom agent about the task or user's needs

By default, Tom agent will analyze the user's message. \
Optionally, you can ask a custom question."""


class TomConsultTool(ToolDefinition[ConsultTomAction, ConsultTomObservation]):
    """Tool for consulting Tom agent."""

    @classmethod
    def create(
        cls,
        enable_rag: bool = True,
        llm_model: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> Sequence["TomConsultTool"]:
        """Initialize TomConsultTool with executor parameters.

        Args:
            enable_rag: Whether to enable RAG in Tom agent
            llm_model: LLM model to use for Tom agent
            api_key: API key for Tom agent's LLM
            api_base: Base URL for Tom agent's LLM

        Returns:
            Sequence containing the initialized TomConsultTool
        """
        file_store = LocalFileStore(root="~/.openhands")

        # Initialize the executor
        executor = TomConsultExecutor(
            file_store=file_store,
            enable_rag=enable_rag,
            llm_model=llm_model,
            api_key=api_key,
            api_base=api_base,
        )

        # Initialize the parent ToolDefinition with the executor
        return [
            cls(
                name="consult_tom_agent",
                description=_DESCRIPTION,
                action_type=ConsultTomAction,
                observation_type=ConsultTomObservation,
                executor=executor,
            )
        ]
