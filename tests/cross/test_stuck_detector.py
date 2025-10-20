import uuid

from openhands.sdk.agent import Agent
from openhands.sdk.conversation.state import ConversationState
from openhands.sdk.conversation.stuck_detector import StuckDetector
from openhands.sdk.event import (
    ActionEvent,
    AgentErrorEvent,
    MessageEvent,
    ObservationEvent,
)
from openhands.sdk.llm import (
    LLM,
    Message,
    MessageToolCall,
    TextContent,
)
from openhands.sdk.workspace import LocalWorkspace
from openhands.tools.execute_bash.definition import (
    ExecuteBashAction,
    ExecuteBashObservation,
)


def test_history_too_short():
    """Test that stuck detector returns False when there are too few events."""
    # Create a minimal agent for testing
    llm = LLM(model="gpt-4o-mini", usage_id="test-llm")
    agent = Agent(llm=llm)
    state = ConversationState.create(
        id=uuid.uuid4(), agent=agent, workspace=LocalWorkspace(working_dir="/tmp")
    )
    stuck_detector = StuckDetector(state)

    # Add a user message
    user_message = MessageEvent(
        source="user",
        llm_message=Message(role="user", content=[TextContent(text="Hello")]),
    )
    state.events.append(user_message)

    # Add a single action-observation pair
    action = ActionEvent(
        source="agent",
        thought=[TextContent(text="I need to run ls command")],
        action=ExecuteBashAction(command="ls"),
        tool_name="execute_bash",
        tool_call_id="call_1",
        tool_call=MessageToolCall(
            id="call_1",
            name="execute_bash",
            arguments='{"command": "ls"}',
            origin="completion",
        ),
        llm_response_id="response_1",
    )
    state.events.append(action)

    observation = ObservationEvent(
        source="environment",
        observation=ExecuteBashObservation(
            output="file1.txt\nfile2.txt", command="ls", exit_code=0
        ),
        action_id=action.id,
        tool_name="execute_bash",
        tool_call_id="call_1",
    )
    state.events.append(observation)

    # Should not be stuck with only one action-observation pair after user message
    assert stuck_detector.is_stuck() is False


def test_repeating_action_observation_not_stuck_less_than_4_repeats():
    """Test detection of repeating action-observation cycles."""
    llm = LLM(model="gpt-4o-mini", usage_id="test-llm")
    agent = Agent(llm=llm)
    state = ConversationState.create(
        id=uuid.uuid4(), agent=agent, workspace=LocalWorkspace(working_dir="/tmp")
    )
    stuck_detector = StuckDetector(state)

    # Add a user message first
    user_message = MessageEvent(
        source="user",
        llm_message=Message(role="user", content=[TextContent(text="Please run ls")]),
    )
    state.events.append(user_message)

    # Add 3 identical action-observation pairs to trigger stuck detection
    for i in range(3):
        action = ActionEvent(
            source="agent",
            thought=[TextContent(text="I need to run ls command")],
            action=ExecuteBashAction(command="ls"),
            tool_name="execute_bash",
            tool_call_id=f"call_{i}",
            tool_call=MessageToolCall(
                id=f"call_{i}",
                name="execute_bash",
                arguments='{"command": "ls"}',
                origin="completion",
            ),
            llm_response_id=f"response_{i}",
        )
        state.events.append(action)

        observation = ObservationEvent(
            source="environment",
            observation=ExecuteBashObservation(
                output="file1.txt\nfile2.txt", command="ls", exit_code=0
            ),
            action_id=action.id,
            tool_name="execute_bash",
            tool_call_id=f"call_{i}",
        )
        state.events.append(observation)

    # Should be stuck with 4 identical action-observation pairs
    assert stuck_detector.is_stuck() is False


def test_repeating_action_observation_stuck():
    """Test detection of repeating action-observation cycles."""
    llm = LLM(model="gpt-4o-mini", usage_id="test-llm")
    agent = Agent(llm=llm)
    state = ConversationState.create(
        id=uuid.uuid4(), agent=agent, workspace=LocalWorkspace(working_dir="/tmp")
    )
    stuck_detector = StuckDetector(state)

    # Add a user message first
    user_message = MessageEvent(
        source="user",
        llm_message=Message(role="user", content=[TextContent(text="Please run ls")]),
    )
    state.events.append(user_message)

    # Add 4 identical action-observation pairs to trigger stuck detection
    for i in range(4):
        action = ActionEvent(
            source="agent",
            thought=[TextContent(text="I need to run ls command")],
            action=ExecuteBashAction(command="ls"),
            tool_name="execute_bash",
            tool_call_id=f"call_{i}",
            tool_call=MessageToolCall(
                id=f"call_{i}",
                name="execute_bash",
                arguments='{"command": "ls"}',
                origin="completion",
            ),
            llm_response_id=f"response_{i}",
        )
        state.events.append(action)

        observation = ObservationEvent(
            source="environment",
            observation=ExecuteBashObservation(
                output="file1.txt\nfile2.txt", command="ls", exit_code=0
            ),
            action_id=action.id,
            tool_name="execute_bash",
            tool_call_id=f"call_{i}",
        )
        state.events.append(observation)

    # Should be stuck with 4 identical action-observation pairs
    assert stuck_detector.is_stuck() is True


def test_repeating_action_error_stuck():
    """Test detection of repeating action-error cycles."""
    llm = LLM(model="gpt-4o-mini", usage_id="test-llm")
    agent = Agent(llm=llm)
    state = ConversationState.create(
        id=uuid.uuid4(), agent=agent, workspace=LocalWorkspace(working_dir="/tmp")
    )
    stuck_detector = StuckDetector(state)

    # Add a user message first
    user_message = MessageEvent(
        source="user",
        llm_message=Message(
            role="user", content=[TextContent(text="Please run the invalid command")]
        ),
    )
    state.events.append(user_message)

    def create_action_and_error(i):
        action = ActionEvent(
            source="agent",
            thought=[TextContent(text="I need to run invalid_command")],
            action=ExecuteBashAction(command="invalid_command"),
            tool_name="execute_bash",
            tool_call_id=f"call_{i}",
            tool_call=MessageToolCall(
                id=f"call_{i}",
                name="execute_bash",
                arguments='{"command": "invalid_command"}',
                origin="completion",
            ),
            llm_response_id=f"response_{i}",
        )
        error = AgentErrorEvent(
            source="agent",
            error="Command 'invalid_command' not found",
            tool_call_id=action.tool_call_id,
            tool_name=action.tool_name,
        )
        return action, error

    # Add 2 identical actions that result in errors
    for i in range(2):
        action, error = create_action_and_error(i)
        state.events.append(action)
        state.events.append(error)

    # Should not stuck with 2 identical action-error pairs
    assert stuck_detector.is_stuck() is False

    # Add 1 more identical action-error pair to trigger stuck detection
    action, error = create_action_and_error(2)
    state.events.append(action)
    state.events.append(error)

    # Should be stuck with 3 identical action-error pairs
    assert stuck_detector.is_stuck() is True


def test_agent_monologue_stuck():
    """Test detection of agent monologue (repeated messages without user input)."""
    llm = LLM(model="gpt-4o-mini", usage_id="test-llm")
    agent = Agent(llm=llm)
    state = ConversationState.create(
        id=uuid.uuid4(), agent=agent, workspace=LocalWorkspace(working_dir="/tmp")
    )
    stuck_detector = StuckDetector(state)

    # Add a user message first
    user_message = MessageEvent(
        source="user",
        llm_message=Message(role="user", content=[TextContent(text="Hello")]),
    )
    state.events.append(user_message)

    # Add 3 consecutive agent messages (monologue)
    for i in range(3):
        agent_message = MessageEvent(
            source="agent",
            llm_message=Message(
                role="assistant", content=[TextContent(text=f"I'm thinking... {i}")]
            ),
        )
        state.events.append(agent_message)

    # Should be stuck due to agent monologue
    assert stuck_detector.is_stuck() is True


def test_not_stuck_with_different_actions():
    """Test that different actions don't trigger stuck detection."""
    llm = LLM(model="gpt-4o-mini", usage_id="test-llm")
    agent = Agent(llm=llm)
    state = ConversationState.create(
        id=uuid.uuid4(), agent=agent, workspace=LocalWorkspace(working_dir="/tmp")
    )
    stuck_detector = StuckDetector(state)

    # Add a user message first
    user_message = MessageEvent(
        source="user",
        llm_message=Message(
            role="user", content=[TextContent(text="Please run different commands")]
        ),
    )
    state.events.append(user_message)

    # Add different actions
    commands = ["ls", "pwd", "whoami", "date"]
    for i, cmd in enumerate(commands):
        action = ActionEvent(
            source="agent",
            thought=[TextContent(text=f"I need to run {cmd} command")],
            action=ExecuteBashAction(command=cmd),
            tool_name="execute_bash",
            tool_call_id=f"call_{i}",
            tool_call=MessageToolCall(
                id=f"call_{i}",
                name="execute_bash",
                arguments=f'{{"command": "{cmd}"}}',
                origin="completion",
            ),
            llm_response_id=f"response_{i}",
        )
        state.events.append(action)

        observation = ObservationEvent(
            source="environment",
            observation=ExecuteBashObservation(
                output=f"output from {cmd}", command=cmd, exit_code=0
            ),
            action_id=action.id,
            tool_name="execute_bash",
            tool_call_id=f"call_{i}",
        )
        state.events.append(observation)

    # Should not be stuck with different actions
    assert stuck_detector.is_stuck() is False


def test_reset_after_user_message():
    """Test that stuck detection resets after a new user message."""
    llm = LLM(model="gpt-4o-mini", usage_id="test-llm")
    agent = Agent(llm=llm)
    state = ConversationState.create(
        id=uuid.uuid4(), agent=agent, workspace=LocalWorkspace(working_dir="/tmp")
    )
    stuck_detector = StuckDetector(state)

    # Add initial user message
    user_message = MessageEvent(
        source="user",
        llm_message=Message(role="user", content=[TextContent(text="Please run ls")]),
    )
    state.events.append(user_message)

    # Add 4 identical action-observation pairs to trigger stuck detection
    for i in range(4):
        action = ActionEvent(
            source="agent",
            thought=[TextContent(text="I need to run ls command")],
            action=ExecuteBashAction(command="ls"),
            tool_name="execute_bash",
            tool_call_id=f"call_{i}",
            tool_call=MessageToolCall(
                id=f"call_{i}",
                name="execute_bash",
                arguments='{"command": "ls"}',
                origin="completion",
            ),
            llm_response_id=f"response_{i}",
        )
        state.events.append(action)

        observation = ObservationEvent(
            source="environment",
            observation=ExecuteBashObservation(
                output="file1.txt\nfile2.txt", command="ls", exit_code=0
            ),
            action_id=action.id,
            tool_name="execute_bash",
            tool_call_id=f"call_{i}",
        )
        state.events.append(observation)

    # Should be stuck
    assert stuck_detector.is_stuck() is True

    # Add a new user message
    new_user_message = MessageEvent(
        source="user",
        llm_message=Message(
            role="user", content=[TextContent(text="Try something else")]
        ),
    )
    state.events.append(new_user_message)

    # Should not be stuck after new user message (history is reset)
    assert stuck_detector.is_stuck() is False

    # Add one more action after user message - still not stuck
    action = ActionEvent(
        source="agent",
        thought=[TextContent(text="I'll try pwd command")],
        action=ExecuteBashAction(command="pwd"),
        tool_name="execute_bash",
        tool_call_id="call_new",
        tool_call=MessageToolCall(
            id="call_new",
            name="execute_bash",
            arguments='{"command": "pwd"}',
            origin="completion",
        ),
        llm_response_id="response_new",
    )
    state.events.append(action)

    observation = ObservationEvent(
        source="environment",
        observation=ExecuteBashObservation(
            output="/home/user", command="pwd", exit_code=0
        ),
        action_id=action.id,
        tool_name="execute_bash",
        tool_call_id="call_new",
    )
    state.events.append(observation)

    # Still not stuck with just one action after user message
    assert stuck_detector.is_stuck() is False
