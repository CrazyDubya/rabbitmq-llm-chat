"""
Improved Chatroom Manager with proper data structures, validation, and management capabilities.
Handles chatroom lifecycle, message management, and participant tracking.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import time
import uuid

from logger import get_logger

logger = get_logger(__name__)


@dataclass
class Message:
    """Data class for chat messages."""
    id: str
    chatroom_name: str
    sender_id: str
    sender_type: str  # 'user' or 'llm'
    content: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            'id': self.id,
            'chatroom_name': self.chatroom_name,
            'sender_id': self.sender_id,
            'sender_type': self.sender_type,
            'content': self.content,
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }


@dataclass 
class Chatroom:
    """Data class for chatroom information."""
    name: str
    creator_id: str
    participants: List[str] = field(default_factory=list)
    llm_participants: List[str] = field(default_factory=list)
    messages: List[Message] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    is_active: bool = True
    max_messages: int = 1000
    topic: str = ""
    description: str = ""
    
    def add_message(self, message: Message) -> None:
        """Add message to chatroom with message limit enforcement."""
        self.messages.append(message)
        
        # Enforce message limit
        if len(self.messages) > self.max_messages:
            removed_count = len(self.messages) - self.max_messages
            self.messages = self.messages[-self.max_messages:]
            logger.debug(f"Removed {removed_count} old messages from chatroom {self.name}")
    
    def get_recent_messages(self, limit: int = 50) -> List[Message]:
        """Get recent messages from chatroom."""
        return self.messages[-limit:] if self.messages else []
    
    def get_participant_count(self) -> int:
        """Get total participant count."""
        return len(self.participants) + len(self.llm_participants)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chatroom to dictionary."""
        return {
            'name': self.name,
            'creator_id': self.creator_id,
            'participants': self.participants.copy(),
            'llm_participants': self.llm_participants.copy(),
            'message_count': len(self.messages),
            'created_at': self.created_at,
            'is_active': self.is_active,
            'topic': self.topic,
            'description': self.description,
            'participant_count': self.get_participant_count()
        }


class ChatroomManager:
    """
    Improved Chatroom Manager with comprehensive chatroom and message management.
    """
    
    def __init__(self):
        """Initialize empty chatroom manager."""
        self._chatrooms: Dict[str, Chatroom] = {}
        self._user_chatrooms: Dict[str, List[str]] = {}  # user_id -> list of chatroom names
        logger.info("Initialized Chatroom Manager")
    
    def create_chatroom(self, name: str, creator_id: str, topic: str = "", 
                       description: str = "", max_messages: int = 1000) -> bool:
        """
        Create a new chatroom.
        
        Args:
            name: Unique chatroom name
            creator_id: ID of the user creating the chatroom
            topic: Optional chatroom topic
            description: Optional chatroom description
            max_messages: Maximum number of messages to retain
            
        Returns:
            True if chatroom created successfully, False if name already exists
        """
        if name in self._chatrooms:
            logger.warning(f"Chatroom {name} already exists")
            return False
        
        if not name.strip():
            logger.error("Chatroom name cannot be empty")
            return False
        
        chatroom = Chatroom(
            name=name,
            creator_id=creator_id,
            topic=topic,
            description=description,
            max_messages=max_messages
        )
        
        self._chatrooms[name] = chatroom
        
        # Add creator to participants
        self.add_user_to_chatroom(name, creator_id)
        
        logger.info(f"Created chatroom: {name} by user {creator_id}")
        return True
    
    def delete_chatroom(self, name: str, user_id: str) -> bool:
        """
        Delete a chatroom (only creator can delete).
        
        Args:
            name: Chatroom name
            user_id: ID of user requesting deletion
            
        Returns:
            True if chatroom deleted, False if not found or unauthorized
        """
        chatroom = self._chatrooms.get(name)
        if not chatroom:
            logger.warning(f"Chatroom {name} not found for deletion")
            return False
        
        if chatroom.creator_id != user_id:
            logger.warning(f"User {user_id} not authorized to delete chatroom {name}")
            return False
        
        # Remove chatroom from user mappings
        for user_chatrooms in self._user_chatrooms.values():
            if name in user_chatrooms:
                user_chatrooms.remove(name)
        
        del self._chatrooms[name]
        logger.info(f"Deleted chatroom: {name}")
        return True
    
    def get_chatroom(self, name: str) -> Optional[Chatroom]:
        """
        Get chatroom by name.
        
        Args:
            name: Chatroom name
            
        Returns:
            Chatroom object or None if not found
        """
        return self._chatrooms.get(name)
    
    def get_all_chatrooms(self) -> List[Chatroom]:
        """
        Get all chatrooms.
        
        Returns:
            List of all chatroom objects
        """
        return list(self._chatrooms.values())
    
    def get_active_chatrooms(self) -> List[Chatroom]:
        """
        Get all active chatrooms.
        
        Returns:
            List of active chatroom objects
        """
        return [room for room in self._chatrooms.values() if room.is_active]
    
    def get_user_chatrooms(self, user_id: str) -> List[Chatroom]:
        """
        Get chatrooms a user is participating in.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of chatrooms user is in
        """
        user_room_names = self._user_chatrooms.get(user_id, [])
        return [self._chatrooms[name] for name in user_room_names if name in self._chatrooms]
    
    def add_user_to_chatroom(self, chatroom_name: str, user_id: str) -> bool:
        """
        Add user to chatroom.
        
        Args:
            chatroom_name: Name of chatroom
            user_id: User identifier
            
        Returns:
            True if user added, False if chatroom not found or user already in room
        """
        chatroom = self._chatrooms.get(chatroom_name)
        if not chatroom:
            logger.warning(f"Chatroom {chatroom_name} not found")
            return False
        
        if user_id in chatroom.participants:
            return True  # Already in room
        
        chatroom.participants.append(user_id)
        
        if user_id not in self._user_chatrooms:
            self._user_chatrooms[user_id] = []
        if chatroom_name not in self._user_chatrooms[user_id]:
            self._user_chatrooms[user_id].append(chatroom_name)
        
        logger.info(f"Added user {user_id} to chatroom {chatroom_name}")
        return True
    
    def remove_user_from_chatroom(self, chatroom_name: str, user_id: str) -> bool:
        """
        Remove user from chatroom.
        
        Args:
            chatroom_name: Name of chatroom
            user_id: User identifier
            
        Returns:
            True if user removed, False if chatroom not found or user not in room
        """
        chatroom = self._chatrooms.get(chatroom_name)
        if not chatroom:
            return False
        
        if user_id in chatroom.participants:
            chatroom.participants.remove(user_id)
            
            if user_id in self._user_chatrooms and chatroom_name in self._user_chatrooms[user_id]:
                self._user_chatrooms[user_id].remove(chatroom_name)
            
            logger.info(f"Removed user {user_id} from chatroom {chatroom_name}")
            return True
        
        return False
    
    def add_llm_to_chatroom(self, chatroom_name: str, llm_id: str) -> bool:
        """
        Add LLM to chatroom.
        
        Args:
            chatroom_name: Name of chatroom
            llm_id: LLM identifier
            
        Returns:
            True if LLM added, False if chatroom not found or LLM already in room
        """
        chatroom = self._chatrooms.get(chatroom_name)
        if not chatroom:
            logger.warning(f"Chatroom {chatroom_name} not found")
            return False
        
        if llm_id in chatroom.llm_participants:
            return True  # Already in room
        
        chatroom.llm_participants.append(llm_id)
        logger.info(f"Added LLM {llm_id} to chatroom {chatroom_name}")
        return True
    
    def remove_llm_from_chatroom(self, chatroom_name: str, llm_id: str) -> bool:
        """
        Remove LLM from chatroom.
        
        Args:
            chatroom_name: Name of chatroom
            llm_id: LLM identifier
            
        Returns:
            True if LLM removed, False if chatroom not found or LLM not in room
        """
        chatroom = self._chatrooms.get(chatroom_name)
        if not chatroom:
            return False
        
        if llm_id in chatroom.llm_participants:
            chatroom.llm_participants.remove(llm_id)
            logger.info(f"Removed LLM {llm_id} from chatroom {chatroom_name}")
            return True
        
        return False
    
    def add_message_to_chatroom(self, chatroom_name: str, sender_id: str, 
                               content: str, sender_type: str = 'user',
                               metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Add message to chatroom.
        
        Args:
            chatroom_name: Name of chatroom
            sender_id: ID of message sender
            content: Message content
            sender_type: Type of sender ('user' or 'llm')
            metadata: Optional metadata dictionary
            
        Returns:
            Message ID if added successfully, None if chatroom not found
        """
        chatroom = self._chatrooms.get(chatroom_name)
        if not chatroom:
            logger.warning(f"Chatroom {chatroom_name} not found for message")
            return None
        
        message_id = str(uuid.uuid4())
        message = Message(
            id=message_id,
            chatroom_name=chatroom_name,
            sender_id=sender_id,
            sender_type=sender_type,
            content=content,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        
        chatroom.add_message(message)
        logger.debug(f"Added message to chatroom {chatroom_name} from {sender_id}")
        return message_id
    
    def get_chatroom_messages(self, chatroom_name: str, limit: int = 50, 
                             offset: int = 0) -> List[Message]:
        """
        Get messages from chatroom with pagination.
        
        Args:
            chatroom_name: Name of chatroom
            limit: Maximum number of messages to return
            offset: Number of messages to skip from the end
            
        Returns:
            List of messages
        """
        chatroom = self._chatrooms.get(chatroom_name)
        if not chatroom:
            return []
        
        messages = chatroom.messages
        if offset > 0:
            messages = messages[:-offset]
        
        return messages[-limit:] if messages else []
    
    def set_chatroom_active(self, chatroom_name: str, is_active: bool) -> bool:
        """
        Set chatroom active status.
        
        Args:
            chatroom_name: Name of chatroom
            is_active: New active status
            
        Returns:
            True if status updated, False if chatroom not found
        """
        chatroom = self._chatrooms.get(chatroom_name)
        if not chatroom:
            return False
        
        chatroom.is_active = is_active
        logger.info(f"Set chatroom {chatroom_name} active status to {is_active}")
        return True
    
    def get_chatroom_stats(self) -> Dict[str, Any]:
        """
        Get chatroom statistics.
        
        Returns:
            Dictionary with chatroom statistics
        """
        total_chatrooms = len(self._chatrooms)
        active_chatrooms = len([room for room in self._chatrooms.values() if room.is_active])
        total_messages = sum(len(room.messages) for room in self._chatrooms.values())
        total_participants = sum(room.get_participant_count() for room in self._chatrooms.values())
        
        return {
            'total_chatrooms': total_chatrooms,
            'active_chatrooms': active_chatrooms,
            'total_messages': total_messages,
            'total_participants': total_participants,
            'average_messages_per_room': total_messages / max(total_chatrooms, 1),
            'average_participants_per_room': total_participants / max(total_chatrooms, 1)
        }
