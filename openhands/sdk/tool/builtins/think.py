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
    fields = [
        SchemaField.create(
            name="thought",
            description="The thought content to log.",
            type=str,
            required=True,
        ),
    ]
    return Schema(
        name=f"{__package__}.input",
        fields=fields,
    )


def make_output_schema() -> Schema:
    return Schema(
        name=f"{__package__}.output",
        fields=[
            SchemaField.create(
                name="content",
                description="Confirmation message.",
                type=str,
                required=True,
            ),
        ],
    )


class ThinkDataConverter(ToolDataConverter):
    def agent_observation(
        self, observation: SchemaInstance
    ) -> Sequence[TextContent | ImageContent]:
        content = observation.data.get("content", "Your thought has been logged.")
        return [TextContent(text=content)]

    def visualize_action(self, action: SchemaInstance) -> Text:
        """Return Rich Text representation with thinking styling."""
        content = Text()

        # Add thinking icon and header
        content.append("🤔 ", style="yellow")
        content.append("Thinking: ", style="bold yellow")

        # Add the thought content with proper formatting
        thought = action.data.get("thought", "")
        if thought:
            # Split into lines for better formatting
            lines = thought.split("\n")
            for i, line in enumerate(lines):
                if i > 0:
                    content.append("\n")
                content.append(line.strip(), style="italic white")

        return content

    def visualize_observation(self, observation: SchemaInstance) -> Text:
        """Return Rich Text representation - empty since action shows the thought."""
        # Don't duplicate the thought display - action already shows it
        return Text()


THINK_DESCRIPTION = """Use the tool to think about something. It will not obtain new information or make any changes to the repository, but just log the thought. Use it when complex reasoning or brainstorming is needed.

Common use cases:
1. When exploring a repository and discovering the source of a bug, call this tool to brainstorm several unique ways of fixing the bug, and assess which change(s) are likely to be simplest and most effective.
2. After receiving test results, use this tool to brainstorm ways to fix failing tests.
3. When planning a complex refactoring, use this tool to outline different approaches and their tradeoffs.
4. When designing a new feature, use this tool to think through architecture decisions and implementation details.
5. When debugging a complex issue, use this tool to organize your thoughts and hypotheses.

The tool simply logs your thought process for better transparency and does not execute any code or make changes."""  # noqa: E501


class ThinkExecutor(ToolExecutor):
    def __call__(self, action: SchemaInstance) -> SchemaInstance:
        return SchemaInstance(
            name="ThinkObservation",
            definition=make_output_schema(),
            data={"content": "Your thought has been logged."},
        )


class ThinkTool(Tool):
    @classmethod
    def create(cls) -> "ThinkTool":
        return cls(
            name="think",
            description=THINK_DESCRIPTION,
            input_schema=make_input_schema(),
            output_schema=make_output_schema(),
            executor=ThinkExecutor(),
            data_converter=ThinkDataConverter(),
            annotations=ToolAnnotations(
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=True,
                openWorldHint=False,
            ),
        )
