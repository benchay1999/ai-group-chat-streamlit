/**
 * useHeartbeat Hook
 * Sends periodic heartbeat signals to track user as online
 */

import { useEffect, useRef } from 'react';
import { roomAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const HEARTBEAT_INTERVAL = 30000; // 30 seconds

/**
 * Custom hook to send periodic heartbeat signals
 * Call this hook on any page where users should be counted as "online"
 * (e.g., Lobby, Dashboard, Game pages)
 */
export const useHeartbeat = () => {
  const { isAuthenticated } = useAuth();
  const intervalRef = useRef(null);

  useEffect(() => {
    // Only send heartbeats for authenticated users
    if (!isAuthenticated) {
      return;
    }

    // Send initial heartbeat immediately
    const sendHeartbeat = async () => {
      try {
        await roomAPI.heartbeat();
      } catch (error) {
        // Silently fail - don't disrupt user experience
        console.debug('Heartbeat failed:', error.message);
      }
    };

    // Send initial heartbeat
    sendHeartbeat();

    // Set up interval for periodic heartbeats
    intervalRef.current = setInterval(sendHeartbeat, HEARTBEAT_INTERVAL);

    // Cleanup on unmount
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isAuthenticated]);

  // Return nothing - this hook is for side effects only
  return null;
};

