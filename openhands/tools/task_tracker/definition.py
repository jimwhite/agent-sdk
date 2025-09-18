import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError
from rich.text import Text

from openhands.sdk import ImageContent, TextContent
from openhands.sdk.logger import get_logger
from openhands.sdk.tool import (
    Schema,
    SchemaField,
    SchemaInstance,
    Tool,
    ToolAnnotations,
    ToolDataConverter,
    ToolExecutor,
)


logger = get_logger(__name__)


class TaskItem(BaseModel):
    title: str = Field(..., description="A brief title for the task.")
    notes: str = Field("", description="Additional details or notes about the task.")
    status: Literal["todo", "in_progress", "done"] = Field(
        "todo",
        description="The current status of the task. "
        "One of 'todo', 'in_progress', or 'done'.",
    )


def make_input_schema() -> Schema:
    return Schema(
        type="action",
        fields=[
            SchemaField.create(
                name="command",
                description="The command to execute. `view` shows the current "
                "task list. `plan` creates or updates the task list based on "
                "provided requirements and progress. Always `view` the current "
                "list before making changes.",
                type=str,
                required=True,
                enum=["view", "plan"],
            ),
            SchemaField.create(
                name="task_list",
                description="The full task list. Required parameter of `plan` command.",
                type=list,
                required=False,
                default=[],
            ),
        ],
    )


def make_output_schema() -> Schema:
    return Schema(
        type="observation",
        fields=[
            SchemaField.create(
                name="content",
                description="The formatted task list or status message",
                type=str,
                required=True,
            ),
            SchemaField.create(
                name="command",
                description="The command that was executed",
                type=str,
                required=True,
            ),
            SchemaField.create(
                name="task_list",
                description="The current task list",
                type=list,
                required=False,
                default=[],
            ),
        ],
    )


class TaskTrackerDataConverter(ToolDataConverter):
    """Data converter for TaskTracker tool."""

    def agent_observation(
        self, observation: SchemaInstance
    ) -> Sequence[TextContent | ImageContent]:
        observation.validate_data()
        content = observation.data.get("content", "")
        return [TextContent(text=content)]

    def visualize_action(self, action: SchemaInstance) -> Text:
        """Return Rich Text representation with task management styling."""
        action.validate_data()
        content = Text()

        command = action.data.get("command", "view")
        task_list = action.data.get("task_list", [])

        # Add command header with icon
        if command == "view":
            content.append("👀 ", style="blue")
            content.append("View Task List", style="blue")
        else:  # plan
            content.append("📋 ", style="green")
            content.append("Update Task List", style="green")

        # Show task count if planning
        if command == "plan" and task_list:
            content.append(f" ({len(task_list)} tasks)", style="dim")

        return content

    def visualize_observation(self, observation: SchemaInstance) -> Text:
        """Return Rich Text representation with task list formatting."""
        observation.validate_data()
        content = Text()

        command = observation.data.get("command", "")
        task_list_data = observation.data.get("task_list", [])

        # Convert task list data to TaskItem objects for processing
        task_list = [TaskItem.model_validate(task) for task in task_list_data]
        if task_list:
            # Count tasks by status
            todo_count = sum(1 for task in task_list if task.status == "todo")
            in_progress_count = sum(
                1 for task in task_list if task.status == "in_progress"
            )
            done_count = sum(1 for task in task_list if task.status == "done")

            # Show status summary
            if command == "plan":
                content.append("✅ ", style="green")
                content.append("Task list updated: ", style="green")
            else:  # view command
                content.append("📋 ", style="blue")
                content.append("Current task list: ", style="blue")

            # Status counts
            status_parts = []
            if todo_count:
                status_parts.append(f"{todo_count} todo")
            if in_progress_count:
                status_parts.append(f"{in_progress_count} in progress")
            if done_count:
                status_parts.append(f"{done_count} done")

            if status_parts:
                content.append(", ".join(status_parts), style="white")
                content.append("\n\n")

            # Show the actual task list
            for i, task in enumerate(task_list, 1):
                # Status icon
                if task.status == "done":
                    content.append("✅ ", style="green")
                elif task.status == "in_progress":
                    content.append("🔄 ", style="yellow")
                else:  # todo
                    content.append("⏳ ", style="blue")

                # Task title
                content.append(f"{i}. {task.title}", style="white")

                # Show notes under the title if present
                if task.notes:
                    content.append("\n   Notes: " + task.notes, style="italic dim")

                if i < len(task_list):
                    content.append("\n")
        else:
            content.append("📝 ", style="blue")
            content.append("Task list is empty", style="dim")

        return content


class TaskTrackerExecutor(ToolExecutor):
    """Executor for the task tracker tool."""

    OUTPUT_NAME = "TaskTrackerObservation"

    def __init__(self, save_dir: str | None = None):
        """Initialize TaskTrackerExecutor.

        Args:
            save_dir: Optional directory to save tasks to. If provided, tasks will be
                     persisted to save_dir/TASKS.md
        """
        self.save_dir = Path(save_dir) if save_dir else None
        self._task_list: list[TaskItem] = []

        # Load existing tasks if save_dir is provided and file exists
        if self.save_dir:
            self._load_tasks()

    def __call__(self, action: SchemaInstance) -> SchemaInstance:
        """Execute the task tracker action."""
        action.validate_data()

        command = action.data.get("command", "view")
        task_list_data = action.data.get("task_list", [])

        if command == "plan":
            # Convert task list data to TaskItem objects
            task_list = [TaskItem.model_validate(task) for task in task_list_data]

            # Update the task list
            self._task_list = task_list
            # Save to file if save_dir is provided
            if self.save_dir:
                self._save_tasks()

            return SchemaInstance(
                name=self.OUTPUT_NAME,
                definition=make_output_schema(),
                data={
                    "content": (
                        f"Task list has been updated with "
                        f"{len(self._task_list)} item(s)."
                    ),
                    "command": command,
                    "task_list": [task.model_dump() for task in self._task_list],
                },
            )
        elif command == "view":
            # Return the current task list
            if not self._task_list:
                return SchemaInstance(
                    name=self.OUTPUT_NAME,
                    definition=make_output_schema(),
                    data={
                        "content": (
                            'No task list found. Use the "plan" command to create one.'
                        ),
                        "command": command,
                        "task_list": [],
                    },
                )
            content = self._format_task_list(self._task_list)
            return SchemaInstance(
                name=self.OUTPUT_NAME,
                definition=make_output_schema(),
                data={
                    "content": content,
                    "command": command,
                    "task_list": [task.model_dump() for task in self._task_list],
                },
            )
        else:
            return SchemaInstance(
                name=self.OUTPUT_NAME,
                definition=make_output_schema(),
                data={
                    "content": f"Unknown command: {command}. "
                    + 'Supported commands are "view" and "plan".',
                    "command": command,
                    "task_list": [],
                },
            )

    def _format_task_list(self, task_list: list[TaskItem]) -> str:
        """Format the task list for display."""
        if not task_list:
            return "No tasks in the list."

        content = "# Task List\n\n"
        for i, task in enumerate(task_list, 1):
            status_icon = {"todo": "⏳", "in_progress": "🔄", "done": "✅"}.get(
                task.status, "⏳"
            )

            title = task.title
            notes = task.notes

            content += f"{i}. {status_icon} {title}\n"
            if notes:
                content += f"   {notes}\n"
            content += "\n"

        return content.strip()

    def _load_tasks(self) -> None:
        """Load tasks from the TASKS.json file if it exists."""
        if not self.save_dir:
            return

        tasks_file = self.save_dir / "TASKS.json"
        if not tasks_file.exists():
            return

        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                self._task_list = [TaskItem.model_validate(d) for d in json.load(f)]
        except (OSError, json.JSONDecodeError, TypeError, ValidationError) as e:
            logger.warning(
                f"Failed to load tasks from {tasks_file}: {e}. Starting with "
                "an empty task list."
            )
            self._task_list = []

    def _save_tasks(self) -> None:
        """Save tasks to the TASKS.json file."""
        if not self.save_dir:
            return

        tasks_file = self.save_dir / "TASKS.json"
        try:
            # Create the directory if it doesn't exist
            self.save_dir.mkdir(parents=True, exist_ok=True)

            with open(tasks_file, "w", encoding="utf-8") as f:
                json.dump([task.model_dump() for task in self._task_list], f, indent=2)
        except OSError as e:
            logger.warning(f"Failed to save tasks to {tasks_file}: {e}")
            pass


# Tool definition with detailed description
TASK_TRACKER_DESCRIPTION = """This tool provides structured task management capabilities for development workflows.
It enables systematic tracking of work items, progress monitoring, and efficient
organization of complex development activities.

The tool maintains visibility into project status and helps communicate
progress effectively to users.

## Application Guidelines

Utilize this tool in the following situations:

1. Multi-phase development work - When projects involve multiple sequential or
   parallel activities
2. Complex implementation tasks - Work requiring systematic planning and
   coordination across multiple components
3. Explicit user request for task organization - When users specifically ask
   for structured task management
4. Multiple concurrent requirements - When users present several work items
   that need coordination
5. Project initiation - Capture and organize user requirements at project start
6. Work commencement - Update task status to in_progress before beginning
   implementation. Maintain focus by limiting active work to one task
7. Task completion - Update status to done and identify any additional work
   that emerged during implementation

## Situations Where Tool Usage Is Unnecessary

Avoid using this tool when:

1. Single atomic tasks that require no decomposition
2. Trivial operations where tracking adds no organizational value
3. Simple activities completable in minimal steps
4. Pure information exchange or discussion

Note: For single straightforward tasks, proceed with direct implementation
rather than creating tracking overhead.

## Usage Scenarios

**Scenario A: Feature Development with Validation**
User request: "Build a user authentication system with login/logout functionality.
Don't forget to include input validation and error handling!"

Response approach: I'll implement a user authentication system with comprehensive
validation. Let me organize this work systematically.

*Task breakdown includes:*
1. Design authentication API endpoints and data models
2. Implement user login/logout controllers with session management
3. Add client-side form validation and error display
4. Create backend input sanitization and security checks
5. Implement comprehensive error handling for edge cases
6. Perform integration testing and fix any issues

**Scenario B: Codebase Refactoring**
User request: "I need to update all instances of the method 'fetchData' to
'retrieveInformation' throughout the entire project"

Response approach: Let me first analyze your codebase to identify all locations
where 'fetchData' appears.

*After code analysis*

I've located 12 occurrences of 'fetchData' across 6 files in your project.
I'll create a systematic plan to update these references.

*Organized task list includes specific file-by-file updates*

**Scenario C: Multi-feature Development**
User request: "Set up a blog platform with these components: admin dashboard,
article management, comment system, and user profiles."

Response approach: I'll help build your blog platform. Let me break down these
components into manageable implementation phases.

*Creates structured plan with each feature decomposed into specific development tasks*

## Counter-examples - Direct Implementation Preferred

**Counter-example A: Simple inquiry**
User request: "What's the syntax for a for loop in JavaScript?"

Response approach: Here's how to write a for loop in JavaScript:

```javascript
for (let i = 0; i < array.length; i++) {
    console.log(array[i]);
}
```

*No task tracking needed - single informational response*

**Counter-example B: Minor modification**
User request: "Please add a docstring to the processPayment function explaining
its parameters."

Response approach: I'll add a docstring to explain the processPayment function.

*Direct edit without task tracking for simple modification*

## Status Management and Workflow

1. **Status Values**: Track work using these states:
   - todo: Not yet initiated
   - in_progress: Currently active (maintain single focus)
   - done: Successfully completed

2. **Workflow Practices**:
   - Update status dynamically as work progresses
   - Mark completion immediately upon task finish
   - Limit active work to ONE task at any given time
   - Complete current activities before initiating new ones
   - Remove obsolete tasks from tracking entirely

3. **Completion Criteria**:
   - Mark tasks as done only when fully achieved
   - Keep status as in_progress if errors, blocks, or partial completion exist
   - Create new tasks for discovered issues or dependencies
   - Never mark done when:
       - Test suites are failing
       - Implementation remains incomplete
       - Unresolved errors persist
       - Required resources are unavailable

4. **Task Organization**:
   - Write precise, actionable descriptions
   - Decompose complex work into manageable units
   - Use descriptive, clear naming conventions

When uncertain, favor using this tool. Proactive task management demonstrates
systematic approach and ensures comprehensive requirement fulfillment."""  # noqa: E501


class TaskTrackerTool(Tool):
    """A Tool subclass that automatically initializes a TaskTrackerExecutor."""

    @classmethod
    def create(cls, save_dir: str | None = None):
        """Initialize TaskTrackerTool with a TaskTrackerExecutor.

        Args:
            save_dir: Optional directory to save tasks to. If provided, tasks will be
                     persisted to save_dir/TASKS.json
        """
        # Create input and output schemas
        input_schema = make_input_schema()
        output_schema = make_output_schema()

        # Initialize the executor
        executor = TaskTrackerExecutor(save_dir=save_dir)

        # Initialize the parent Tool with the executor
        return cls(
            name="task_tracker",
            description=TASK_TRACKER_DESCRIPTION,
            input_schema=input_schema,
            output_schema=output_schema,
            annotations=ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=True,
                openWorldHint=False,
            ),
            executor=executor,
            data_converter=TaskTrackerDataConverter(),
        )
