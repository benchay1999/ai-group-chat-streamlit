"""
API Key Manager for Round-Robin Distribution
Manages multiple OpenAI API keys and distributes them across rooms in a round-robin fashion.

This module provides thread-safe, round-robin distribution of API keys to prevent
rate limiting when running with 100+ concurrent users.
"""

import threading
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class APIKeyManagerError(Exception):
    """Custom exception for API Key Manager errors."""
    pass


class APIKeyManager:
    """
    Thread-safe manager for distributing API keys across rooms using round-robin.
    
    This class ensures that multiple concurrent room creations don't skip keys
    or assign the same key to multiple rooms simultaneously.
    """
    
    def __init__(self, api_keys: List[str]):
        """
        Initialize the API key manager with a list of keys.
        
        Args:
            api_keys: List of OpenAI API keys to distribute
            
        Raises:
            APIKeyManagerError: If no valid API keys are provided
            ValueError: If api_keys is not a list or contains invalid types
        """
        # Validate input type
        if not isinstance(api_keys, list):
            raise ValueError(f"api_keys must be a list, got {type(api_keys)}")
        
        # Filter and validate keys
        if not api_keys or not any(api_keys):
            raise APIKeyManagerError(
                "APIKeyManager requires at least one valid API key. "
                "Set OPENAI_API_KEY or OPENAI_API_KEYS environment variable."
            )
        
        # Filter out None/empty keys and validate types
        valid_keys = []
        for i, key in enumerate(api_keys):
            if key and isinstance(key, str):
                valid_keys.append(key.strip())
            elif key is not None:
                logger.warning(f"Skipping invalid API key at index {i}: not a string (type: {type(key)})")
        
        if not valid_keys:
            raise APIKeyManagerError(
                "No valid API keys found after filtering. "
                "All provided keys were None, empty, or invalid type."
            )
        
        self.api_keys = valid_keys
        self.current_index = 0
        self.lock = threading.Lock()
        self.total_assigned = 0  # Track total keys assigned for logging
        
        logger.info(f"🔑 APIKeyManager initialized with {len(self.api_keys)} API key(s)")
        print(f"🔑 APIKeyManager initialized with {len(self.api_keys)} API key(s)")
        # Note: Key format validation removed - actual validation happens on API calls
    
    def get_next_api_key(self) -> Tuple[str, int]:
        """
        Get the next API key in round-robin fashion.
        Thread-safe operation that increments the counter atomically.
        
        Returns:
            Tuple of (api_key, key_index) where key_index is 0-based
            
        Raises:
            APIKeyManagerError: If no API keys are available (should never happen after init)
        """
        with self.lock:
            # Defensive check (should never fail after successful init)
            if not self.api_keys:
                raise APIKeyManagerError("No API keys available - manager is in invalid state")
            
            # Get current key and index
            key_index = self.current_index
            api_key = self.api_keys[key_index]
            
            # Defensive check for valid key
            if not api_key or not isinstance(api_key, str):
                logger.error(f"Invalid API key at index {key_index}: {type(api_key)}")
                raise APIKeyManagerError(f"API key at index {key_index} is invalid")
            
            # Increment counter for next call (wrap around)
            self.current_index = (self.current_index + 1) % len(self.api_keys)
            self.total_assigned += 1
            
            # Log assignment (use 1-based indexing for human readability)
            if len(self.api_keys) > 1:
                logger.info(f"Assigned API key #{key_index + 1}/{len(self.api_keys)} (total rooms: {self.total_assigned})")
                print(f"🔑 Assigned API key #{key_index + 1}/{len(self.api_keys)} (total rooms: {self.total_assigned})")
            
            return api_key, key_index
    
    def get_api_key_by_index(self, index: int) -> Optional[str]:
        """
        Get a specific API key by index.
        Useful for debugging or retrieving the key assigned to a specific room.
        
        Args:
            index: 0-based index of the API key
            
        Returns:
            API key at the specified index, or None if index is out of range
        """
        with self.lock:  # Thread-safe read
            if not isinstance(index, int):
                logger.warning(f"get_api_key_by_index called with non-int index: {type(index)}")
                return None
            
            if 0 <= index < len(self.api_keys):
                return self.api_keys[index]
            
            logger.warning(f"API key index {index} out of range (0-{len(self.api_keys)-1})")
            return None
    
    def get_key_count(self) -> int:
        """
        Get the total number of API keys available.
        
        Returns:
            Number of API keys
        """
        return len(self.api_keys)
    
    def get_stats(self) -> dict:
        """
        Get statistics about API key usage.
        
        Returns:
            Dictionary with stats: total_keys, current_index, total_assigned
        """
        with self.lock:
            return {
                "total_keys": len(self.api_keys),
                "current_index": self.current_index,
                "total_assigned": self.total_assigned,
                "next_key_index": self.current_index
            }

