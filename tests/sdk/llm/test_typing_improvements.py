"""Test typing improvements for issue #458."""

from openhands.sdk.llm import LLM


def test_llm_metrics_always_initialized():
    """Test that LLM._metrics is always initialized and not None."""
    llm = LLM(model="gpt-3.5-turbo")

    # Metrics should be accessible without any None checks
    metrics = llm.metrics
    assert metrics is not None
    assert metrics.model_name == "gpt-3.5-turbo"


def test_llm_telemetry_always_initialized():
    """Test that LLM._telemetry is always initialized and not None."""
    llm = LLM(model="gpt-3.5-turbo")

    # Telemetry should be accessible without any None checks
    # Access the private attribute directly to test it's not None
    assert llm._telemetry is not None
    assert llm._telemetry.model_name == "gpt-3.5-turbo"


def test_llm_initialization_with_different_models():
    """Test that metrics and telemetry are properly initialized for different models."""
    models = ["gpt-4", "claude-3-sonnet", "gemini-pro"]

    for model in models:
        llm = LLM(model=model)

        # Both metrics and telemetry should be initialized with correct model name
        assert llm.metrics.model_name == model
        assert llm._telemetry.model_name == model


def test_llm_restore_metrics():
    """Test that metrics can be restored without None checks."""
    from openhands.sdk.llm.utils.metrics import Metrics

    llm = LLM(model="gpt-3.5-turbo")

    # Create new metrics and restore them
    new_metrics = Metrics(model_name="test-model")
    llm.restore_metrics(new_metrics)

    # Should be able to access metrics without None checks
    restored_metrics = llm.metrics
    assert restored_metrics.model_name == "test-model"
    assert restored_metrics is new_metrics


def test_tool_create_returns_single_type():
    """Test that Tool.create method signature returns Self, not a union type.

    This test verifies that the typing improvement for Tool.create is working.
    The base Tool.create method now returns Self instead of Self | list[Self].
    """
    # Import the actual tools to test the create method signature
    # These should return single instances, not union types
    import os

    from openhands.tools.execute_bash.definition import BashTool
    from openhands.tools.str_replace_editor.definition import FileEditorTool

    bash_tool = BashTool.create(working_dir=os.getcwd())
    assert isinstance(bash_tool, BashTool)
    assert bash_tool.name == "execute_bash"

    file_tool = FileEditorTool.create()
    assert isinstance(file_tool, FileEditorTool)
    assert file_tool.name == "str_replace_editor"

    # The return types should be consistent and not require type narrowing
    # This test ensures that the typing improvement eliminates the need for
    # isinstance checks or assert statements to narrow union types
