/**
 * Game Context
 * Global state management for room code, player ID, and game status
 */

import { createContext, useContext, useState } from 'react';

const GameContext = createContext();

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

  const value = {
    roomCode,
    playerId,
    selectedRoom,
    joinRoom,
    leaveRoom,
    selectRoom,
  };

  return <GameContext.Provider value={value}>{children}</GameContext.Provider>;
};

export default GameContext;

