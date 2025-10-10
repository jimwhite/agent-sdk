"""Tests for delegation tools."""

import pytest
from unittest.mock import Mock

from openhands.tools.delegation.definition import (
    DelegateAction,
    DelegateObservation,
    DelegationTool,
)
from openhands.tools.delegation.impl import DelegateExecutor
from openhands.sdk.delegation.manager import DelegationManager


def test_delegate_action_spawn():
    """Test DelegateAction for spawn operation."""
    action = DelegateAction(
        operation="spawn",
        task="Test task for sub-agent"
    )
    
    assert action.operation == "spawn"
    assert action.task == "Test task for sub-agent"
    assert action.sub_conversation_id is None
    assert action.message is None


def test_delegate_action_send():
    """Test DelegateAction for send operation."""
    action = DelegateAction(
        operation="send",
        sub_conversation_id="sub-123",
        message="Hello sub-agent"
    )
    
    assert action.operation == "send"
    assert action.sub_conversation_id == "sub-123"
    assert action.message == "Hello sub-agent"
    assert action.task is None


def test_delegate_action_close():
    """Test DelegateAction for close operation."""
    action = DelegateAction(
        operation="close",
        sub_conversation_id="sub-123"
    )
    
    assert action.operation == "close"
    assert action.sub_conversation_id == "sub-123"
    assert action.task is None
    assert action.message is None


def test_delegate_observation():
    """Test DelegateObservation."""
    observation = DelegateObservation(
        sub_conversation_id="sub-123",
        status="created",
        message="Sub-agent created successfully",
        result="Task completed"
    )
    
    assert observation.sub_conversation_id == "sub-123"
    assert observation.status == "created"
    assert observation.message == "Sub-agent created successfully"
    assert observation.result == "Task completed"


def test_delegate_executor_spawn():
    """Test DelegateExecutor spawn operation."""
    # Mock delegation manager
    mock_manager = Mock(spec=DelegationManager)
    mock_sub_conversation = Mock()
    mock_sub_conversation.id = "sub-456"
    mock_manager.spawn_sub_agent.return_value = mock_sub_conversation
    
    # Mock parent conversation
    mock_parent_conversation = Mock()
    
    # Create executor
    executor = DelegateExecutor(mock_manager)
    executor.parent_conversation = mock_parent_conversation
    
    # Create spawn action
    action = DelegateAction(
        operation="spawn",
        task="Analyze code quality"
    )
    
    # Execute action
    observation = executor.execute(action)
    
    # Verify
    assert isinstance(observation, DelegateObservation)
    assert observation.sub_conversation_id == "sub-456"
    assert observation.status == "created"
    assert "Sub-agent created successfully" in observation.message
    
    # Verify manager was called
    mock_manager.spawn_sub_agent.assert_called_once_with(
        mock_parent_conversation, "Analyze code quality"
    )


def test_delegate_executor_send():
    """Test DelegateExecutor send operation."""
    # Mock delegation manager
    mock_manager = Mock(spec=DelegationManager)
    mock_manager.send_to_sub_agent.return_value = True
    
    # Create executor
    executor = DelegateExecutor(mock_manager)
    
    # Create send action
    action = DelegateAction(
        operation="send",
        sub_conversation_id="sub-123",
        message="Please analyze the file"
    )
    
    # Execute action
    observation = executor.execute(action)
    
    # Verify
    assert isinstance(observation, DelegateObservation)
    assert observation.sub_conversation_id == "sub-123"
    assert observation.status == "message_sent"
    assert "Message sent to sub-agent" in observation.message
    
    # Verify manager was called
    mock_manager.send_to_sub_agent.assert_called_once_with(
        "sub-123", "Please analyze the file"
    )


def test_delegate_executor_send_failure():
    """Test DelegateExecutor send operation failure."""
    # Mock delegation manager
    mock_manager = Mock(spec=DelegationManager)
    mock_manager.send_to_sub_agent.return_value = False
    
    # Create executor
    executor = DelegateExecutor(mock_manager)
    
    # Create send action
    action = DelegateAction(
        operation="send",
        sub_conversation_id="non-existent",
        message="Test message"
    )
    
    # Execute action
    observation = executor.execute(action)
    
    # Verify
    assert isinstance(observation, DelegateObservation)
    assert observation.sub_conversation_id == "non-existent"
    assert observation.status == "error"
    assert "Failed to send message" in observation.message


def test_delegate_executor_status():
    """Test DelegateExecutor status operation."""
    # Mock delegation manager
    mock_manager = Mock(spec=DelegationManager)
    mock_manager.get_sub_agent_status.return_value = "active"
    
    # Create executor
    executor = DelegateExecutor(mock_manager)
    
    # Create status action
    action = DelegateAction(
        operation="status",
        sub_conversation_id="sub-123"
    )
    
    # Execute action
    observation = executor.execute(action)
    
    # Verify
    assert isinstance(observation, DelegateObservation)
    assert observation.sub_conversation_id == "sub-123"
    assert observation.status == "active"
    assert "Sub-agent status: active" in observation.message
    
    # Verify manager was called
    mock_manager.get_sub_agent_status.assert_called_once_with("sub-123")


def test_delegate_executor_close():
    """Test DelegateExecutor close operation."""
    # Mock delegation manager
    mock_manager = Mock(spec=DelegationManager)
    mock_manager.close_sub_agent.return_value = True
    
    # Create executor
    executor = DelegateExecutor(mock_manager)
    
    # Create close action
    action = DelegateAction(
        operation="close",
        sub_conversation_id="sub-123"
    )
    
    # Execute action
    observation = executor.execute(action)
    
    # Verify
    assert isinstance(observation, DelegateObservation)
    assert observation.sub_conversation_id == "sub-123"
    assert observation.status == "closed"
    assert "Sub-agent closed successfully" in observation.message
    
    # Verify manager was called
    mock_manager.close_sub_agent.assert_called_once_with("sub-123")


def test_delegate_executor_close_failure():
    """Test DelegateExecutor close operation failure."""
    # Mock delegation manager
    mock_manager = Mock(spec=DelegationManager)
    mock_manager.close_sub_agent.return_value = False
    
    # Create executor
    executor = DelegateExecutor(mock_manager)
    
    # Create close action
    action = DelegateAction(
        operation="close",
        sub_conversation_id="non-existent"
    )
    
    # Execute action
    observation = executor.execute(action)
    
    # Verify
    assert isinstance(observation, DelegateObservation)
    assert observation.sub_conversation_id == "non-existent"
    assert observation.status == "error"
    assert "Failed to close sub-agent" in observation.message


def test_delegation_tool_creation():
    """Test DelegationTool creation."""
    mock_manager = Mock(spec=DelegationManager)
    
    tool = DelegationTool.create(delegation_manager=mock_manager)
    
    assert tool is not None
    assert hasattr(tool, 'executor')
    assert isinstance(tool.executor, DelegateExecutor)
    assert tool.executor.delegation_manager == mock_manager