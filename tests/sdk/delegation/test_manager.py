"""Tests for DelegationManager."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from openhands.sdk.delegation.manager import DelegationManager
from openhands.sdk.conversation import Conversation


def test_delegation_manager_init():
    """Test DelegationManager initialization."""
    manager = DelegationManager()
    
    assert manager.conversations == {}
    assert manager.parent_to_children == {}
    assert manager.child_to_parent == {}


def test_spawn_sub_agent():
    """Test spawning a sub-agent."""
    manager = DelegationManager()
    
    # Mock parent conversation
    parent_conversation = Mock(spec=Conversation)
    parent_conversation.id = "parent-123"
    parent_conversation.workspace = Path("/test/workspace")
    
    # Mock the get_worker_agent function
    with patch('openhands.sdk.delegation.manager.get_worker_agent') as mock_get_worker:
        mock_agent = Mock()
        mock_get_worker.return_value = mock_agent
        
        # Mock Conversation constructor
        with patch('openhands.sdk.delegation.manager.Conversation') as mock_conversation_class:
            mock_sub_conversation = Mock(spec=Conversation)
            mock_sub_conversation.id = "sub-456"
            mock_conversation_class.return_value = mock_sub_conversation
            
            # Spawn sub-agent
            result = manager.spawn_sub_agent(parent_conversation, "Test task")
            
            # Verify result
            assert result == mock_sub_conversation
            assert "sub-456" in manager.conversations
            assert manager.conversations["sub-456"] == mock_sub_conversation
            assert "parent-123" in manager.parent_to_children
            assert "sub-456" in manager.parent_to_children["parent-123"]
            assert manager.child_to_parent["sub-456"] == "parent-123"
            
            # Verify worker agent was created
            mock_get_worker.assert_called_once()
            
            # Verify sub-conversation was created with correct parameters
            mock_conversation_class.assert_called_once_with(
                agent=mock_agent,
                workspace=parent_conversation.workspace
            )


def test_send_to_sub_agent_success():
    """Test sending message to sub-agent successfully."""
    manager = DelegationManager()
    
    # Setup mock sub-conversation
    mock_sub_conversation = Mock(spec=Conversation)
    mock_sub_conversation.send_message_async = Mock()
    manager.conversations["sub-456"] = mock_sub_conversation
    
    # Send message
    result = manager.send_to_sub_agent("sub-456", "Test message")
    
    # Verify
    assert result is True
    mock_sub_conversation.send_message_async.assert_called_once_with("Test message")


def test_send_to_sub_agent_not_found():
    """Test sending message to non-existent sub-agent."""
    manager = DelegationManager()
    
    # Send message to non-existent sub-agent
    result = manager.send_to_sub_agent("non-existent", "Test message")
    
    # Verify
    assert result is False


def test_close_sub_agent_success():
    """Test closing sub-agent successfully."""
    manager = DelegationManager()
    
    # Setup relationships
    parent_id = "parent-123"
    sub_id = "sub-456"
    
    mock_sub_conversation = Mock(spec=Conversation)
    manager.conversations[sub_id] = mock_sub_conversation
    manager.parent_to_children[parent_id] = {sub_id}
    manager.child_to_parent[sub_id] = parent_id
    
    # Close sub-agent
    result = manager.close_sub_agent(sub_id)
    
    # Verify cleanup
    assert result is True
    assert sub_id not in manager.conversations
    assert sub_id not in manager.parent_to_children[parent_id]
    assert sub_id not in manager.child_to_parent


def test_close_sub_agent_not_found():
    """Test closing non-existent sub-agent."""
    manager = DelegationManager()
    
    # Close non-existent sub-agent
    result = manager.close_sub_agent("non-existent")
    
    # Verify
    assert result is False


def test_multiple_sub_agents():
    """Test managing multiple sub-agents."""
    manager = DelegationManager()
    
    # Mock parent conversation
    parent_conversation = Mock(spec=Conversation)
    parent_conversation.id = "parent-123"
    parent_conversation.workspace = Path("/test/workspace")
    
    with patch('openhands.sdk.delegation.manager.get_worker_agent') as mock_get_worker:
        mock_agent = Mock()
        mock_get_worker.return_value = mock_agent
        
        with patch('openhands.sdk.delegation.manager.Conversation') as mock_conversation_class:
            # Create multiple sub-conversations
            sub1 = Mock(spec=Conversation)
            sub1.id = "sub-1"
            sub2 = Mock(spec=Conversation)
            sub2.id = "sub-2"
            
            mock_conversation_class.side_effect = [sub1, sub2]
            
            # Spawn multiple sub-agents
            result1 = manager.spawn_sub_agent(parent_conversation, "Task 1")
            result2 = manager.spawn_sub_agent(parent_conversation, "Task 2")
            
            # Verify both sub-agents are tracked
            assert result1 == sub1
            assert result2 == sub2
            assert len(manager.conversations) == 2
            assert len(manager.parent_to_children["parent-123"]) == 2
            assert "sub-1" in manager.parent_to_children["parent-123"]
            assert "sub-2" in manager.parent_to_children["parent-123"]


def test_get_sub_agent_status():
    """Test getting sub-agent status."""
    manager = DelegationManager()
    
    # Setup mock sub-conversation
    mock_sub_conversation = Mock(spec=Conversation)
    manager.conversations["sub-456"] = mock_sub_conversation
    
    # Get status for existing sub-agent
    status = manager.get_sub_agent_status("sub-456")
    assert status == "active"
    
    # Get status for non-existent sub-agent
    status = manager.get_sub_agent_status("non-existent")
    assert status == "not_found"