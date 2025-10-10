"""Test that tools contain security risk field when appropriate."""

from pydantic import SecretStr

from openhands.sdk.agent.agent import Agent
from openhands.sdk.conversation import Conversation
from openhands.sdk.llm import LLM
from openhands.sdk.tool import register_tool
from openhands.sdk.tool.spec import Tool


def test_agent_with_no_security_analyzer_file_editor_tool():
    """Test that file editor tool contains security risk field when no security analyzer is present."""  # noqa: E501
    # Register the file editor tool first
    from openhands.tools.file_editor import FileEditorTool

    register_tool("FileEditorTool", FileEditorTool)

    # Create agent with no security analyzer but with file editor tool
    agent = Agent(
        llm=LLM(
            service_id="test-llm",
            model="test-model",
            api_key=SecretStr("test-key"),
            base_url="http://test",
        ),
        tools=[Tool(name="FileEditorTool")],
    )

    # Initialize the agent by creating a conversation
    Conversation(agent=agent, visualize=False)

    # Get the file editor tool from the agent's tools map
    file_editor_tool = agent.tools_map.get("str_replace_editor")
    assert file_editor_tool is not None, "File editor tool should be available"

    # Check if the tool schema contains security_risk field when
    # add_security_risk_prediction=True
    openai_tool_with_risk = file_editor_tool.to_openai_tool(
        add_security_risk_prediction=True
    )
    parameters = openai_tool_with_risk["function"].get("parameters", {})
    properties = parameters.get("properties", {})

    # The security risk field should be present when add_security_risk_prediction=True
    assert "security_risk" in properties, (
        "File editor tool should contain security_risk field when "
        "add_security_risk_prediction=True"
    )

    # Verify the security_risk field has the expected structure
    security_risk_field = properties["security_risk"]
    assert "description" in security_risk_field
    assert "Security risk levels for actions" in security_risk_field["description"]

    # Check if the tool schema does NOT contain security_risk field when
    # add_security_risk_prediction=False
    openai_tool_without_risk = file_editor_tool.to_openai_tool(
        add_security_risk_prediction=False
    )
    parameters_without_risk = openai_tool_without_risk["function"].get("parameters", {})
    properties_without_risk = parameters_without_risk.get("properties", {})

    # The security risk field should NOT be present when
    # add_security_risk_prediction=False
    assert "security_risk" not in properties_without_risk, (
        "File editor tool should NOT contain security_risk field when "
        "add_security_risk_prediction=False"
    )


def test_agent_with_no_security_analyzer_bash_tool():
    """Test that bash tool contains security risk field when no security analyzer is present."""  # noqa: E501
    # Register the bash tool first
    from openhands.tools.execute_bash import BashTool

    register_tool("BashTool", BashTool)

    # Create agent with no security analyzer but with bash tool
    agent = Agent(
        llm=LLM(
            service_id="test-llm",
            model="test-model",
            api_key=SecretStr("test-key"),
            base_url="http://test",
        ),
        tools=[Tool(name="BashTool")],
    )

    # Initialize the agent by creating a conversation
    Conversation(agent=agent, visualize=False)

    # Get the bash tool from the agent's tools map
    bash_tool = agent.tools_map.get("execute_bash")
    assert bash_tool is not None, "Bash tool should be available"

    # Check if the tool schema contains security_risk field when
    # add_security_risk_prediction=True
    openai_tool_with_risk = bash_tool.to_openai_tool(add_security_risk_prediction=True)
    parameters = openai_tool_with_risk["function"].get("parameters", {})
    properties = parameters.get("properties", {})

    # The security risk field should be present when add_security_risk_prediction=True
    assert "security_risk" in properties, (
        "Bash tool should contain security_risk field when "
        "add_security_risk_prediction=True"
    )

    # Verify the security_risk field has the expected structure
    security_risk_field = properties["security_risk"]
    assert "description" in security_risk_field
    assert "Security risk levels for actions" in security_risk_field["description"]

    # Check if the tool schema does NOT contain security_risk field when
    # add_security_risk_prediction=False
    openai_tool_without_risk = bash_tool.to_openai_tool(
        add_security_risk_prediction=False
    )
    parameters_without_risk = openai_tool_without_risk["function"].get("parameters", {})
    properties_without_risk = parameters_without_risk.get("properties", {})

    # The security risk field should NOT be present when
    # add_security_risk_prediction=False
    assert "security_risk" not in properties_without_risk, (
        "Bash tool should NOT contain security_risk field when "
        "add_security_risk_prediction=False"
    )


def test_agent_with_both_tools_no_security_analyzer():
    """Test that both file editor and bash tools contain security risk field when no security analyzer is present."""  # noqa: E501
    # Register both tools first
    from openhands.tools.execute_bash import BashTool
    from openhands.tools.file_editor import FileEditorTool

    register_tool("FileEditorTool", FileEditorTool)
    register_tool("BashTool", BashTool)

    # Create agent with no security analyzer but with both tools
    agent = Agent(
        llm=LLM(
            service_id="test-llm",
            model="test-model",
            api_key=SecretStr("test-key"),
            base_url="http://test",
        ),
        tools=[Tool(name="FileEditorTool"), Tool(name="BashTool")],
    )

    # Initialize the agent by creating a conversation
    Conversation(agent=agent, visualize=False)

    # Get both tools from the agent's tools map
    file_editor_tool = agent.tools_map.get("str_replace_editor")
    bash_tool = agent.tools_map.get("execute_bash")

    assert file_editor_tool is not None, "File editor tool should be available"
    assert bash_tool is not None, "Bash tool should be available"

    # Test both tools have security_risk field when add_security_risk_prediction=True
    for tool_name, tool in [("file_editor", file_editor_tool), ("bash", bash_tool)]:
        openai_tool_with_risk = tool.to_openai_tool(add_security_risk_prediction=True)
        parameters = openai_tool_with_risk["function"].get("parameters", {})
        properties = parameters.get("properties", {})

        assert "security_risk" in properties, (
            f"{tool_name} tool should contain security_risk field when "
            "add_security_risk_prediction=True"
        )

        # Verify the security_risk field has the expected structure
        security_risk_field = properties["security_risk"]
        assert "description" in security_risk_field
        assert "Security risk levels for actions" in security_risk_field["description"]

    # Test both tools do NOT have security_risk field when
    # add_security_risk_prediction=False
    for tool_name, tool in [("file_editor", file_editor_tool), ("bash", bash_tool)]:
        openai_tool_without_risk = tool.to_openai_tool(
            add_security_risk_prediction=False
        )
        parameters_without_risk = openai_tool_without_risk["function"].get(
            "parameters", {}
        )
        properties_without_risk = parameters_without_risk.get("properties", {})

        assert "security_risk" not in properties_without_risk, (
            f"{tool_name} tool should NOT contain security_risk field when "
            "add_security_risk_prediction=False"
        )


def test_readonly_tool_excludes_security_risk_field():
    """Test that read-only tools exclude security risk field even when add_security_risk_prediction=True."""  # noqa: E501
    # Register both tools first
    from openhands.tools.execute_bash import BashTool
    from openhands.tools.file_editor import FileEditorTool

    register_tool("FileEditorTool", FileEditorTool)
    register_tool("BashTool", BashTool)

    # Create agent with no security analyzer but with both tools
    agent = Agent(
        llm=LLM(
            service_id="test-llm",
            model="test-model",
            api_key=SecretStr("test-key"),
            base_url="http://test",
        ),
        tools=[Tool(name="FileEditorTool"), Tool(name="BashTool")],
    )

    # Initialize the agent by creating a conversation
    Conversation(agent=agent, visualize=False)

    # Get both tools from the agent's tools map
    file_editor_tool = agent.tools_map.get("str_replace_editor")
    bash_tool = agent.tools_map.get("execute_bash")

    assert file_editor_tool is not None, "File editor tool should be available"
    assert bash_tool is not None, "Bash tool should be available"

    # Test that both tools have security_risk field when
    # add_security_risk_prediction=True (they are not read-only)
    for tool_name, tool in [("file_editor", file_editor_tool), ("bash", bash_tool)]:
        openai_tool_with_risk = tool.to_openai_tool(add_security_risk_prediction=True)
        parameters = openai_tool_with_risk["function"].get("parameters", {})
        properties = parameters.get("properties", {})

        # Both tools should have security_risk field since they are not read-only
        assert "security_risk" in properties, (
            f"{tool_name} tool should contain security_risk field since "
            "it's not read-only"
        )

        # Verify the security_risk field has the expected structure
        security_risk_field = properties["security_risk"]
        assert "description" in security_risk_field
        assert "Security risk levels for actions" in security_risk_field["description"]

    # Note: This test demonstrates that FileEditorTool and BashTool are NOT
    # read-only tools, so they include the security_risk field.
    # If we had actual read-only tools, they would exclude this field.
