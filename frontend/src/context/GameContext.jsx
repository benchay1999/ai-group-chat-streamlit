/**
 * Game Context
 * Global state management for room code, player ID, and game status
 * Includes session persistence for reconnection support
 */

import { createContext, useContext, useState } from 'react';

const GameContext = createContext();

const ACTIVE_SESSION_KEY = 'ai-group-chat-active-session';

export const useGame = () => {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error('useGame must be used within a GameProvider');
  }
  return context;
};

export const GameProvider = ({ children }) => {
  const [roomCode, setRoomCode] = useState(null);
  const [playerId, setPlayerId] = useState(null);
  const [selectedRoom, setSelectedRoom] = useState(null);

  const joinRoom = (code, id) => {
    setRoomCode(code);
    setPlayerId(id);
  };

  const leaveRoom = () => {
    setRoomCode(null);
    setPlayerId(null);
    setSelectedRoom(null);
  };

  const selectRoom = (room) => {
    setSelectedRoom(room);
  };

  /**
   * Save active session to localStorage for reconnection support
   * @param {string} roomCode - Room code
   * @param {string} playerId - Player ID
   * @param {string} roomStatus - Room status ('waiting' | 'in_progress')
   */
  const saveActiveSession = (roomCode, playerId, roomStatus) => {
    try {
      const sessionData = {
        roomCode,
        playerId,
        roomStatus,
        timestamp: Date.now()
      };
      localStorage.setItem(ACTIVE_SESSION_KEY, JSON.stringify(sessionData));
      console.log('💾 Saved active session:', sessionData);
    } catch (error) {
      console.error('Failed to save active session:', error);
    }
  };

  /**
   * Get active session from localStorage
   * @returns {Object|null} Session data or null if no active session
   */
  const getActiveSession = () => {
    try {
      const data = localStorage.getItem(ACTIVE_SESSION_KEY);
      if (!data) return null;
      
      const session = JSON.parse(data);
      console.log('📖 Retrieved active session:', session);
      return session;
    } catch (error) {
      console.error('Failed to get active session:', error);
      return null;
    }
  };

  /**
   * Clear active session from localStorage
   */
  const clearActiveSession = () => {
    try {
      localStorage.removeItem(ACTIVE_SESSION_KEY);
      console.log('🗑️ Cleared active session');
    } catch (error) {
      console.error('Failed to clear active session:', error);
    }
  };

  /**
   * Check if there's a stored active session
   * @returns {boolean} True if active session exists
   */
  const hasActiveSession = () => {
    const session = getActiveSession();
    return session !== null && session.roomCode && session.playerId;
  };

  const value = {
    roomCode,
    playerId,
    selectedRoom,
    joinRoom,
    leaveRoom,
    selectRoom,
    saveActiveSession,
    getActiveSession,
    clearActiveSession,
    hasActiveSession,
  };

  return <GameContext.Provider value={value}>{children}</GameContext.Provider>;
};

export default GameContext;

