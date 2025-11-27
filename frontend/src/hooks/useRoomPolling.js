/**
 * Room Polling Hook
 * Polls room info for waiting screen updates
 */

import { useEffect, useState, useRef } from 'react';
import { roomAPI } from '../services/api';

const DEFAULT_INTERVAL = 2000; // 2 seconds

export const useRoomPolling = (roomCode, interval = DEFAULT_INTERVAL, enabled = true) => {
  const [roomInfo, setRoomInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const consecutiveErrorsRef = useRef(0);

  useEffect(() => {
    if (!roomCode || !enabled) {
      setLoading(false);
      return;
    }

    const poll = async () => {
      try {
        const data = await roomAPI.getRoomInfo(roomCode);
        setRoomInfo(data);
        setError(null);
        setLoading(false);
        consecutiveErrorsRef.current = 0; // Reset error count on success
      } catch (err) {
        console.error('Error polling room info:', err);
        consecutiveErrorsRef.current += 1;
        
        // Only set error state if we fail multiple times in a row
        // This prevents flickering error messages during transient network issues/rate limits
        if (consecutiveErrorsRef.current >= 3) {
          setError(err.message);
        }
        
        // Don't set loading to false immediately if we're just retrying
        // Keep previous data visible
      }
    };

    // Initial poll
    poll();

    // Set up interval
    intervalRef.current = setInterval(poll, interval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [roomCode, interval, enabled]);

  return { roomInfo, loading, error };
};

export default useRoomPolling;
