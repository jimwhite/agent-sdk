from collections.abc import Sequence

from rich.text import Text

from openhands.sdk.llm.message import ImageContent, TextContent
from openhands.sdk.tool.schema import Schema, SchemaField, SchemaInstance
from openhands.sdk.tool.tool import (
    Tool,
    ToolAnnotations,
    ToolDataConverter,
    ToolExecutor,
)


def make_input_schema() -> Schema:
    return Schema(
        name="openhands.sdk.tool.builtins.finish.input",
        fields=[
            SchemaField.create(
                name="message",
                description="Final message to send to the user.",
                type=str,
                required=True,
            ),
            SchemaField.create(
                name="security_risk",
                description="The LLM's assessment of the safety risk of this "
                "action. See the SECURITY_RISK_ASSESSMENT section in the system "
                "prompt for risk level definitions.",
                type=str,
                required=True,
                enum=["LOW", "MEDIUM", "HIGH", "UNKNOWN"],
            ),
        ],
    )


def make_output_schema() -> Schema:
    return Schema(
        name="openhands.sdk.tool.builtins.finish.output",
        fields=[
            SchemaField.create(
                name="message",
                description="Final message sent to the user.",
                type=str,
                required=True,
            ),
        ],
    )


class FinishDataConverter(ToolDataConverter):
    def agent_observation(
        self, observation: SchemaInstance
    ) -> Sequence[TextContent | ImageContent]:
        message = observation.data.get("message", "")
        return [TextContent(text=message)]

    def visualize_action(self, action: SchemaInstance) -> Text:
        """Return Rich Text representation of this action."""
        content = Text()
        content.append("Finish with message:\n", style="bold blue")
        message = action.data.get("message", "")
        content.append(message)
        return content

    def visualize_observation(self, observation: SchemaInstance) -> Text:
        """Return Rich Text representation - empty since action shows the message."""
        # Don't duplicate the finish message display - action already shows it
        return Text()


TOOL_DESCRIPTION = """Signals the completion of the current task or conversation.

Use this tool when:
- You have successfully completed the user's requested task
- You cannot proceed further due to technical limitations or missing information

The message should include:
- A clear summary of actions taken and their results
- Any next steps for the user
- Explanation if you're unable to complete the task
- Any follow-up questions if more information is needed
"""


class FinishExecutor(ToolExecutor):
    def __call__(self, action: SchemaInstance) -> SchemaInstance:
        message = action.data.get("message", "")
        return SchemaInstance(
            schema=make_output_schema(),
            data={"message": message},
        )


class FinishTool(Tool):
    @classmethod
    def create(cls) -> "FinishTool":
        return cls(
            name="finish",
            description=TOOL_DESCRIPTION,
            input_schema=make_input_schema(),
            output_schema=make_output_schema(),
            executor=FinishExecutor(),
            data_converter=FinishDataConverter(),
            annotations=ToolAnnotations(
                title="finish",
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=True,
                openWorldHint=False,
            ),
        )
