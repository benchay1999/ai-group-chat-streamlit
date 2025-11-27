"""
API Key Manager for Round-Robin Distribution
Manages multiple OpenAI API keys and distributes them across rooms in a round-robin fashion.

This module provides thread-safe, round-robin distribution of API keys to prevent
rate limiting when running with 100+ concurrent users.
"""

import threading
import logging
import time
from typing import List, Optional, Tuple, Dict
from enum import Enum

logger = logging.getLogger(__name__)


# FIX 7.4: API Key Health Status
class KeyHealth(str, Enum):
    """Health status of an API key."""
    HEALTHY = "healthy"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


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
        
        # FIX 7.4: Track health status per API key
        self.key_health: Dict[int, KeyHealth] = {i: KeyHealth.HEALTHY for i in range(len(valid_keys))}
        self.key_last_error: Dict[int, float] = {}  # Timestamp of last error
        self.key_error_count: Dict[int, int] = {i: 0 for i in range(len(valid_keys))}
        self.health_check_interval = 300  # Seconds to recover from rate limit (5 minutes)
        
        logger.info(f"🔑 APIKeyManager initialized with {len(self.api_keys)} API key(s)")
        print(f"🔑 APIKeyManager initialized with {len(self.api_keys)} API key(s)")
        # Note: Key format validation removed - actual validation happens on API calls
    
    def get_next_api_key(self) -> Tuple[str, int]:
        """
        Get the next API key in round-robin fashion, skipping unhealthy keys.
        Thread-safe operation that increments the counter atomically.
        
        FIX 7.4: Now checks key health and rejects if all keys are unhealthy.
        
        Returns:
            Tuple of (api_key, key_index) where key_index is 0-based
            
        Raises:
            APIKeyManagerError: If no healthy API keys are available
        """
        with self.lock:
            # Defensive check (should never fail after successful init)
            if not self.api_keys:
                raise APIKeyManagerError("No API keys available - manager is in invalid state")
            
            # FIX 7.4: Check if any keys are healthy (use unlocked version - we already hold the lock)
            if not self._has_healthy_keys_unlocked():
                raise APIKeyManagerError(
                    "All API keys are currently unhealthy (rate limited or error). "
                    "Please try again in a few minutes or contact administrator."
                )
            
            # FIX 7.4: Find next healthy key (skip unhealthy ones)
            attempts = 0
            max_attempts = len(self.api_keys)
            
            while attempts < max_attempts:
                key_index = self.current_index
                
                # Increment for next iteration
                self.current_index = (self.current_index + 1) % len(self.api_keys)
                attempts += 1
                
                # Check if this key is healthy
                if self.key_health.get(key_index, KeyHealth.HEALTHY) == KeyHealth.HEALTHY:
                    api_key = self.api_keys[key_index]
                    
                    # Defensive check for valid key
                    if not api_key or not isinstance(api_key, str):
                        logger.error(f"Invalid API key at index {key_index}: {type(api_key)}")
                        continue  # Skip to next key
                    
                    self.total_assigned += 1
                    
                    # Log assignment (use 1-based indexing for human readability)
                    if len(self.api_keys) > 1:
                        logger.info(f"Assigned API key #{key_index + 1}/{len(self.api_keys)} (total rooms: {self.total_assigned})")
                        print(f"🔑 Assigned API key #{key_index + 1}/{len(self.api_keys)} (total rooms: {self.total_assigned})")
                    
                    return api_key, key_index
            
            # Should not reach here if has_healthy_keys() returned True, but defensive
            raise APIKeyManagerError("Failed to find healthy API key after checking all keys")
    
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
                "next_key_index": self.current_index,
                # FIX 7.4: Include health information
                "healthy_keys": sum(1 for h in self.key_health.values() if h == KeyHealth.HEALTHY),
                "rate_limited_keys": sum(1 for h in self.key_health.values() if h == KeyHealth.RATE_LIMITED),
                "error_keys": sum(1 for h in self.key_health.values() if h == KeyHealth.ERROR),
            }
    
    # FIX 7.4: Health tracking methods
    def report_key_failure(self, key_index: int, is_rate_limit: bool = False):
        """
        Report a failure for a specific API key.
        
        Args:
            key_index: Index of the failed key
            is_rate_limit: True if failure was due to rate limiting
        """
        with self.lock:
            if 0 <= key_index < len(self.api_keys):
                self.key_last_error[key_index] = time.time()
                self.key_error_count[key_index] = self.key_error_count.get(key_index, 0) + 1
                
                if is_rate_limit:
                    self.key_health[key_index] = KeyHealth.RATE_LIMITED
                    logger.warning(f"⚠️ API key #{key_index + 1} rate limited (will recover in {self.health_check_interval}s)")
                else:
                    self.key_health[key_index] = KeyHealth.ERROR
                    logger.error(f"❌ API key #{key_index + 1} reported error ({self.key_error_count[key_index]} total)")
    
    def report_key_success(self, key_index: int):
        """
        Report successful usage of an API key (clears error status).
        
        Args:
            key_index: Index of the successful key
        """
        with self.lock:
            if 0 <= key_index < len(self.api_keys):
                if self.key_health[key_index] != KeyHealth.HEALTHY:
                    logger.info(f"✅ API key #{key_index + 1} recovered")
                self.key_health[key_index] = KeyHealth.HEALTHY
                self.key_error_count[key_index] = 0
    
    def _has_healthy_keys_unlocked(self) -> bool:
        """
        Internal method to check for healthy keys WITHOUT acquiring lock.
        Must be called from within a locked context.
        
        Returns:
            True if at least one healthy key is available
        """
        current_time = time.time()
        
        # Auto-recover rate-limited keys after interval
        for key_index, health in self.key_health.items():
            if health == KeyHealth.RATE_LIMITED:
                last_error = self.key_last_error.get(key_index, 0)
                if current_time - last_error > self.health_check_interval:
                    logger.info(f"🔄 Auto-recovering API key #{key_index + 1} from rate limit")
                    self.key_health[key_index] = KeyHealth.HEALTHY
        
        # Check if any keys are healthy
        healthy_count = sum(1 for h in self.key_health.values() if h == KeyHealth.HEALTHY)
        return healthy_count > 0
    
    def has_healthy_keys(self) -> bool:
        """
        Check if any API keys are currently healthy.
        Automatically recovers rate-limited keys after health_check_interval.
        
        Returns:
            True if at least one healthy key is available
        """
        with self.lock:
            return self._has_healthy_keys_unlocked()
    
    def get_healthy_key_indices(self) -> List[int]:
        """
        Get list of indices for healthy API keys.
        
        Returns:
            List of key indices that are healthy
        """
        with self.lock:
            return [i for i, h in self.key_health.items() if h == KeyHealth.HEALTHY]

