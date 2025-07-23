"""
Improved LLM Registry with proper interface design, type hints, and error handling.
Manages registration and routing of Language Model services.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import time

from logger import get_logger

logger = get_logger(__name__)


class LLMStatus(Enum):
    """LLM service status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class LLMInfo:
    """Data class for LLM information."""
    llm_id: str
    name: str
    endpoint: str
    api_key: str
    chatrooms: List[str]
    status: LLMStatus = LLMStatus.ACTIVE
    created_at: float = None
    last_seen: float = None
    error_count: int = 0
    max_errors: int = 5
    
    def __post_init__(self):
        """Set default timestamps."""
        if self.created_at is None:
            self.created_at = time.time()
        if self.last_seen is None:
            self.last_seen = time.time()
    
    def update_last_seen(self) -> None:
        """Update last seen timestamp."""
        self.last_seen = time.time()
    
    def increment_error(self) -> None:
        """Increment error count and update status if necessary."""
        self.error_count += 1
        if self.error_count >= self.max_errors:
            self.status = LLMStatus.ERROR
            logger.warning(f"LLM {self.llm_id} marked as ERROR due to repeated failures")
    
    def reset_errors(self) -> None:
        """Reset error count and status."""
        self.error_count = 0
        if self.status == LLMStatus.ERROR:
            self.status = LLMStatus.ACTIVE
            logger.info(f"LLM {self.llm_id} status reset to ACTIVE")


class LLMRegistry:
    """
    Improved LLM Registry with proper interface design and management capabilities.
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._llms: Dict[str, LLMInfo] = {}
        self._api_key_to_id: Dict[str, str] = {}
        logger.info("Initialized LLM Registry")
    
    def register_llm(self, llm_id: str, name: str, endpoint: str, 
                    api_key: str, chatrooms: List[str]) -> bool:
        """
        Register a new LLM service.
        
        Args:
            llm_id: Unique identifier for the LLM
            name: Human-readable name
            endpoint: API endpoint URL
            api_key: API authentication key
            chatrooms: List of chatroom names this LLM can join
            
        Returns:
            True if registration successful, False if LLM already exists
        """
        if llm_id in self._llms:
            logger.warning(f"LLM {llm_id} already registered")
            return False
        
        if api_key in self._api_key_to_id:
            logger.error(f"API key already in use for LLM {self._api_key_to_id[api_key]}")
            return False
        
        llm_info = LLMInfo(
            llm_id=llm_id,
            name=name,
            endpoint=endpoint,
            api_key=api_key,
            chatrooms=chatrooms.copy()
        )
        
        self._llms[llm_id] = llm_info
        self._api_key_to_id[api_key] = llm_id
        
        logger.info(f"Registered LLM: {llm_id} ({name}) for chatrooms: {chatrooms}")
        return True
    
    def unregister_llm(self, llm_id: str) -> bool:
        """
        Unregister an LLM service.
        
        Args:
            llm_id: ID of LLM to unregister
            
        Returns:
            True if unregistration successful, False if LLM not found
        """
        if llm_id not in self._llms:
            logger.warning(f"LLM {llm_id} not found for unregistration")
            return False
        
        llm_info = self._llms[llm_id]
        del self._api_key_to_id[llm_info.api_key]
        del self._llms[llm_id]
        
        logger.info(f"Unregistered LLM: {llm_id}")
        return True
    
    def get_llm_by_id(self, llm_id: str) -> Optional[LLMInfo]:
        """
        Get LLM information by ID.
        
        Args:
            llm_id: LLM identifier
            
        Returns:
            LLMInfo object or None if not found
        """
        return self._llms.get(llm_id)
    
    def get_llm_by_api_key(self, api_key: str) -> Optional[LLMInfo]:
        """
        Get LLM information by API key.
        
        Args:
            api_key: API authentication key
            
        Returns:
            LLMInfo object or None if not found
        """
        llm_id = self._api_key_to_id.get(api_key)
        if llm_id:
            return self._llms.get(llm_id)
        return None
    
    def get_llm_id_by_api_key(self, api_key: str) -> Optional[str]:
        """
        Get LLM ID by API key (backward compatibility).
        
        Args:
            api_key: API authentication key
            
        Returns:
            LLM ID or None if not found
        """
        return self._api_key_to_id.get(api_key)
    
    def get_all_llms(self) -> List[LLMInfo]:
        """
        Get all registered LLMs.
        
        Returns:
            List of LLMInfo objects
        """
        return list(self._llms.values())
    
    def get_active_llms(self) -> List[LLMInfo]:
        """
        Get all active LLMs.
        
        Returns:
            List of active LLMInfo objects
        """
        return [llm for llm in self._llms.values() if llm.status == LLMStatus.ACTIVE]
    
    def get_llms_for_chatroom(self, chatroom_name: str) -> List[LLMInfo]:
        """
        Get all LLMs that can participate in a specific chatroom.
        
        Args:
            chatroom_name: Name of the chatroom
            
        Returns:
            List of LLMInfo objects that can join the chatroom
        """
        return [
            llm for llm in self._llms.values()
            if chatroom_name in llm.chatrooms and llm.status == LLMStatus.ACTIVE
        ]
    
    def update_llm_status(self, llm_id: str, status: LLMStatus) -> bool:
        """
        Update LLM status.
        
        Args:
            llm_id: LLM identifier
            status: New status
            
        Returns:
            True if update successful, False if LLM not found
        """
        if llm_id not in self._llms:
            return False
        
        old_status = self._llms[llm_id].status
        self._llms[llm_id].status = status
        self._llms[llm_id].update_last_seen()
        
        if old_status != status:
            logger.info(f"LLM {llm_id} status changed from {old_status.value} to {status.value}")
        
        return True
    
    def record_llm_error(self, llm_id: str) -> bool:
        """
        Record an error for an LLM service.
        
        Args:
            llm_id: LLM identifier
            
        Returns:
            True if error recorded, False if LLM not found
        """
        if llm_id not in self._llms:
            return False
        
        self._llms[llm_id].increment_error()
        return True
    
    def reset_llm_errors(self, llm_id: str) -> bool:
        """
        Reset error count for an LLM service.
        
        Args:
            llm_id: LLM identifier
            
        Returns:
            True if errors reset, False if LLM not found
        """
        if llm_id not in self._llms:
            return False
        
        self._llms[llm_id].reset_errors()
        return True
    
    def add_chatroom_to_llm(self, llm_id: str, chatroom_name: str) -> bool:
        """
        Add a chatroom to an LLM's participation list.
        
        Args:
            llm_id: LLM identifier
            chatroom_name: Name of chatroom to add
            
        Returns:
            True if chatroom added, False if LLM not found or chatroom already added
        """
        if llm_id not in self._llms:
            return False
        
        if chatroom_name not in self._llms[llm_id].chatrooms:
            self._llms[llm_id].chatrooms.append(chatroom_name)
            logger.info(f"Added chatroom {chatroom_name} to LLM {llm_id}")
            return True
        
        return False
    
    def remove_chatroom_from_llm(self, llm_id: str, chatroom_name: str) -> bool:
        """
        Remove a chatroom from an LLM's participation list.
        
        Args:
            llm_id: LLM identifier
            chatroom_name: Name of chatroom to remove
            
        Returns:
            True if chatroom removed, False if LLM not found or chatroom not in list
        """
        if llm_id not in self._llms:
            return False
        
        if chatroom_name in self._llms[llm_id].chatrooms:
            self._llms[llm_id].chatrooms.remove(chatroom_name)
            logger.info(f"Removed chatroom {chatroom_name} from LLM {llm_id}")
            return True
        
        return False
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with registry statistics
        """
        total = len(self._llms)
        active = len([llm for llm in self._llms.values() if llm.status == LLMStatus.ACTIVE])
        inactive = len([llm for llm in self._llms.values() if llm.status == LLMStatus.INACTIVE])
        error = len([llm for llm in self._llms.values() if llm.status == LLMStatus.ERROR])
        maintenance = len([llm for llm in self._llms.values() if llm.status == LLMStatus.MAINTENANCE])
        
        return {
            'total_llms': total,
            'active': active,
            'inactive': inactive,
            'error': error,
            'maintenance': maintenance,
            'chatrooms_covered': len(set(
                chatroom for llm in self._llms.values() 
                for chatroom in llm.chatrooms
            ))
        }
