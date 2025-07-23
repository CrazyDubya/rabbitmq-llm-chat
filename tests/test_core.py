"""
Test suite for RabbitMQ LLM Chat Platform.
Demonstrates testing framework setup and basic functionality tests.
"""

import pytest
import os
import sys
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from llm_registry import LLMRegistry, LLMStatus, LLMInfo
from chatroom_manager import ChatroomManager, Message, Chatroom


class TestConfig:
    """Test configuration management."""
    
    def test_config_initialization(self):
        """Test basic configuration initialization."""
        config = Config()
        assert config.get('rabbitmq', 'host') == 'localhost'
        assert config.get('rabbitmq', 'port') == 5672
        assert config.get('web', 'debug') == False
    
    def test_environment_override(self):
        """Test environment variable override."""
        os.environ['RABBITMQ_HOST'] = 'test.example.com'
        config = Config()
        assert config.get('rabbitmq', 'host') == 'test.example.com'
        del os.environ['RABBITMQ_HOST']
    
    def test_config_validation(self):
        """Test configuration validation."""
        config = Config()
        issues = config.validate()
        # Should have issues with default configuration
        assert len(issues) >= 2


class TestLLMRegistry:
    """Test LLM Registry functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.registry = LLMRegistry()
    
    def test_register_llm(self):
        """Test LLM registration."""
        success = self.registry.register_llm(
            llm_id='test_llm',
            name='Test LLM',
            endpoint='http://localhost:8000',
            api_key='test_key',
            chatrooms=['test_room']
        )
        assert success == True
        
        # Test duplicate registration fails
        success = self.registry.register_llm(
            llm_id='test_llm',
            name='Test LLM 2',
            endpoint='http://localhost:8001',
            api_key='test_key_2',
            chatrooms=['test_room']
        )
        assert success == False
    
    def test_get_llm_by_api_key(self):
        """Test LLM retrieval by API key."""
        self.registry.register_llm(
            llm_id='test_llm',
            name='Test LLM',
            endpoint='http://localhost:8000',
            api_key='test_key',
            chatrooms=['test_room']
        )
        
        llm = self.registry.get_llm_by_api_key('test_key')
        assert llm is not None
        assert llm.llm_id == 'test_llm'
        assert llm.name == 'Test LLM'
        
        # Test non-existent key
        llm = self.registry.get_llm_by_api_key('non_existent')
        assert llm is None
    
    def test_llm_status_management(self):
        """Test LLM status tracking."""
        self.registry.register_llm(
            llm_id='test_llm',
            name='Test LLM',
            endpoint='http://localhost:8000',
            api_key='test_key',
            chatrooms=['test_room']
        )
        
        # Test status update
        success = self.registry.update_llm_status('test_llm', LLMStatus.MAINTENANCE)
        assert success == True
        
        llm = self.registry.get_llm_by_id('test_llm')
        assert llm.status == LLMStatus.MAINTENANCE
    
    def test_error_tracking(self):
        """Test error tracking functionality."""
        self.registry.register_llm(
            llm_id='test_llm',
            name='Test LLM',
            endpoint='http://localhost:8000',
            api_key='test_key',
            chatrooms=['test_room']
        )
        
        llm = self.registry.get_llm_by_id('test_llm')
        initial_error_count = llm.error_count
        
        # Record error
        self.registry.record_llm_error('test_llm')
        llm = self.registry.get_llm_by_id('test_llm')
        assert llm.error_count == initial_error_count + 1
    
    def test_registry_stats(self):
        """Test registry statistics."""
        # Register multiple LLMs
        self.registry.register_llm('llm1', 'LLM 1', 'http://localhost:8001', 'key1', ['room1'])
        self.registry.register_llm('llm2', 'LLM 2', 'http://localhost:8002', 'key2', ['room1', 'room2'])
        
        stats = self.registry.get_registry_stats()
        assert stats['total_llms'] == 2
        assert stats['active'] == 2
        assert stats['chatrooms_covered'] == 2


class TestChatroomManager:
    """Test Chatroom Manager functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.manager = ChatroomManager()
    
    def test_create_chatroom(self):
        """Test chatroom creation."""
        success = self.manager.create_chatroom(
            name='test_room',
            creator_id='user1',
            topic='Test Topic',
            description='Test Description'
        )
        assert success == True
        
        # Test duplicate creation fails
        success = self.manager.create_chatroom(
            name='test_room',
            creator_id='user2'
        )
        assert success == False
    
    def test_add_participants(self):
        """Test adding participants to chatroom."""
        self.manager.create_chatroom('test_room', 'user1')
        
        # Add user
        success = self.manager.add_user_to_chatroom('test_room', 'user2')
        assert success == True
        
        # Add LLM
        success = self.manager.add_llm_to_chatroom('test_room', 'llm1')
        assert success == True
        
        chatroom = self.manager.get_chatroom('test_room')
        assert 'user2' in chatroom.participants
        assert 'llm1' in chatroom.llm_participants
    
    def test_message_management(self):
        """Test message handling."""
        self.manager.create_chatroom('test_room', 'user1')
        
        # Add message
        message_id = self.manager.add_message_to_chatroom(
            chatroom_name='test_room',
            sender_id='user1',
            content='Hello, world!',
            sender_type='user'
        )
        assert message_id is not None
        
        # Get messages
        messages = self.manager.get_chatroom_messages('test_room', limit=10)
        assert len(messages) == 1
        assert messages[0].content == 'Hello, world!'
        assert messages[0].sender_id == 'user1'
    
    def test_chatroom_stats(self):
        """Test chatroom statistics."""
        # Create multiple chatrooms with messages
        self.manager.create_chatroom('room1', 'user1')
        self.manager.create_chatroom('room2', 'user2')
        
        self.manager.add_message_to_chatroom('room1', 'user1', 'Message 1')
        self.manager.add_message_to_chatroom('room1', 'user1', 'Message 2')
        self.manager.add_message_to_chatroom('room2', 'user2', 'Message 3')
        
        stats = self.manager.get_chatroom_stats()
        assert stats['total_chatrooms'] == 2
        assert stats['total_messages'] == 3
        assert stats['active_chatrooms'] == 2


class TestIntegration:
    """Integration tests for multiple components."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.llm_registry = LLMRegistry()
        self.chatroom_manager = ChatroomManager()
    
    def test_llm_chatroom_integration(self):
        """Test LLM and chatroom integration."""
        # Register LLM
        self.llm_registry.register_llm(
            llm_id='test_llm',
            name='Test LLM',
            endpoint='http://localhost:8000',
            api_key='test_key',
            chatrooms=['test_room']
        )
        
        # Create chatroom
        self.chatroom_manager.create_chatroom('test_room', 'user1')
        
        # Add LLM to chatroom
        self.chatroom_manager.add_llm_to_chatroom('test_room', 'test_llm')
        
        # Verify LLM can access chatroom
        llm = self.llm_registry.get_llm_by_id('test_llm')
        assert 'test_room' in llm.chatrooms
        
        chatroom = self.chatroom_manager.get_chatroom('test_room')
        assert 'test_llm' in chatroom.llm_participants


if __name__ == '__main__':
    pytest.main([__file__, '-v'])