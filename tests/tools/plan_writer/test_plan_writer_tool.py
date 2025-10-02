"""Tests for PlanWriterTool functionality."""

from openhands.tools.plan_writer.definition import (
    PlanWriterAction,
    PlanWriterObservation,
)


def test_write_plan_success(plan_writer_executor, temp_workspace):
    """Test successful plan writing."""
    content = "# Test Plan\n\nThis is a test plan."
    action = PlanWriterAction(command="write", content=content, filename="test_plan.md")
    result = plan_writer_executor(action)

    assert isinstance(result, PlanWriterObservation)
    assert result.command == "write"
    assert result.filename == "test_plan.md"
    assert result.error is None
    assert "successfully" in result.output

    # Verify file was created
    plan_file = temp_workspace / "test_plan.md"
    assert plan_file.exists()
    assert plan_file.read_text() == content


def test_write_plan_default_filename(plan_writer_executor, temp_workspace):
    """Test writing plan with default filename."""
    content = "# Default Plan\n\nThis uses the default filename."
    action = PlanWriterAction(command="write", content=content)
    result = plan_writer_executor(action)

    assert isinstance(result, PlanWriterObservation)
    assert result.filename == "PLAN.md"
    assert result.error is None

    # Verify file was created with default name
    plan_file = temp_workspace / "PLAN.md"
    assert plan_file.exists()
    assert plan_file.read_text() == content


def test_append_to_existing_plan(plan_writer_executor, temp_workspace):
    """Test appending content to an existing plan."""
    # First, create a plan
    initial_content = "# Initial Plan\n\nInitial content."
    write_action = PlanWriterAction(command="write", content=initial_content)
    plan_writer_executor(write_action)

    # Then append to it
    append_content = "\n\n## Additional Section\n\nAppended content."
    append_action = PlanWriterAction(command="append", content=append_content)
    result = plan_writer_executor(append_action)

    assert isinstance(result, PlanWriterObservation)
    assert result.command == "append"
    assert result.error is None
    assert "appended successfully" in result.output

    # Verify content was appended
    plan_file = temp_workspace / "PLAN.md"
    final_content = plan_file.read_text()
    assert initial_content in final_content
    assert append_content in final_content
    assert final_content == initial_content + append_content


def test_append_to_nonexistent_plan(plan_writer_executor):
    """Test appending to a plan that doesn't exist."""
    action = PlanWriterAction(command="append", content="Some content")
    result = plan_writer_executor(action)

    assert isinstance(result, PlanWriterObservation)
    assert result.command == "append"
    assert result.error is not None
    assert "does not exist" in result.error


def test_invalid_filename_extension(plan_writer_executor):
    """Test writing with invalid filename extension."""
    action = PlanWriterAction(command="write", content="content", filename="plan.txt")
    result = plan_writer_executor(action)

    assert isinstance(result, PlanWriterObservation)
    assert result.error is not None
    assert "must end with .md" in result.error


def test_filename_path_traversal_protection(plan_writer_executor):
    """Test protection against path traversal in filename."""
    action = PlanWriterAction(
        command="write", content="content", filename="../../../malicious.md"
    )
    result = plan_writer_executor(action)

    assert isinstance(result, PlanWriterObservation)
    assert result.error is not None
    assert "cannot contain path separators" in result.error


def test_overwrite_existing_plan(plan_writer_executor, temp_workspace):
    """Test overwriting an existing plan file."""
    # Create initial plan
    initial_content = "# Original Plan\n\nOriginal content."
    action1 = PlanWriterAction(command="write", content=initial_content)
    plan_writer_executor(action1)

    # Overwrite with new content
    new_content = "# New Plan\n\nCompletely new content."
    action2 = PlanWriterAction(command="write", content=new_content)
    result = plan_writer_executor(action2)

    assert isinstance(result, PlanWriterObservation)
    assert result.error is None

    # Verify file was overwritten
    plan_file = temp_workspace / "PLAN.md"
    assert plan_file.read_text() == new_content
    assert initial_content not in plan_file.read_text()


def test_unknown_command(plan_writer_executor):
    """Test handling of unknown commands."""

    # Create a mock action to bypass Pydantic validation
    class MockAction:
        def __init__(self):
            self.command = "delete"
            self.content = "content"
            self.filename = "PLAN.md"

    mock_action = MockAction()
    result = plan_writer_executor(mock_action)

    assert isinstance(result, PlanWriterObservation)
    assert result.error is not None
    assert "Unknown command" in result.error


def test_empty_content(plan_writer_executor, temp_workspace):
    """Test writing empty content."""
    action = PlanWriterAction(command="write", content="")
    result = plan_writer_executor(action)

    assert isinstance(result, PlanWriterObservation)
    assert result.error is None

    # Verify empty file was created
    plan_file = temp_workspace / "PLAN.md"
    assert plan_file.exists()
    assert plan_file.read_text() == ""


def test_large_content(plan_writer_executor, temp_workspace):
    """Test writing large content."""
    large_content = "# Large Plan\n\n" + "".join(f"Line {i}\n" for i in range(1000))
    action = PlanWriterAction(command="write", content=large_content)
    result = plan_writer_executor(action)

    assert isinstance(result, PlanWriterObservation)
    assert result.error is None
    assert "characters" in result.output  # Should mention character count

    # Verify large file was created
    plan_file = temp_workspace / "PLAN.md"
    assert plan_file.exists()
    assert len(plan_file.read_text()) > 8000
