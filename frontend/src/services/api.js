/**
 * API Service Client
 * Handles all REST API communication with the backend
 */

import axios from 'axios';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BACKEND_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Room Management APIs
export const roomAPI = {
  /**
   * Create a new room
   * @param {Object} data - { max_humans: number, total_players: number }
   * @returns {Promise} Response with room_code, room_name, etc.
   */
  createRoom: async (data) => {
    const response = await api.post('/api/rooms/create', data);
    return response.data;
  },

  /**
   * List available rooms (waiting status)
   * @param {number} page - Page number (0-indexed)
   * @param {number} perPage - Rooms per page
   * @returns {Promise} Paginated room list
   */
  listRooms: async (page = 0, perPage = 10) => {
    const response = await api.get('/api/rooms/list', {
      params: { page, per_page: perPage },
    });
    return response.data;
  },

  /**
   * Get room information
   * @param {string} roomCode - Room code
   * @returns {Promise} Room metadata
   */
  getRoomInfo: async (roomCode) => {
    const response = await api.get(`/api/rooms/${roomCode}/info`);
    return response.data;
  },

  /**
   * Join a room
   * @param {string} roomCode - Room code
   * @param {Object} playerData - Player data (optional, server assigns ID)
   * @returns {Promise} Join result with player_id and can_start
   */
  joinRoom: async (roomCode, playerData = {}) => {
    const response = await api.post(`/api/rooms/${roomCode}/join`, playerData);
    return response.data;
  },

  /**
   * Leave a room
   * @param {string} roomCode - Room code
   * @param {string} playerId - Player ID
   * @returns {Promise} Leave result
   */
  leaveRoom: async (roomCode, playerId) => {
    const response = await api.post(`/api/rooms/${roomCode}/leave`, {
      player_id: playerId,
    });
    return response.data;
  },

  /**
   * Get game state (polling endpoint)
   * @param {string} roomCode - Room code
   * @param {string} playerId - Player ID
   * @returns {Promise} Current game state
   */
  getGameState: async (roomCode, playerId) => {
    const response = await api.get(`/api/rooms/${roomCode}/state`, {
      params: { player_id: playerId },
    });
    return response.data;
  },

  /**
   * Send a chat message
   * @param {string} roomCode - Room code
   * @param {string} playerId - Player ID
   * @param {string} message - Message content
   * @returns {Promise} Success status
   */
  sendMessage: async (roomCode, playerId, message) => {
    const response = await api.post(`/api/rooms/${roomCode}/message`, {
      player_id: playerId,
      message,
    });
    return response.data;
  },

  /**
   * Cast a vote
   * @param {string} roomCode - Room code
   * @param {string} playerId - Player ID
   * @param {string} votedFor - Target player ID
   * @returns {Promise} Success status
   */
  castVote: async (roomCode, playerId, votedFor) => {
    const response = await api.post(`/api/rooms/${roomCode}/vote`, {
      player_id: playerId,
      voted_for: votedFor,
    });
    return response.data;
  },

  /**
   * Health check
   * @returns {Promise} Server health status
   */
  healthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};

/**
 * Get WebSocket URL
 * @param {string} roomCode - Room code
 * @param {string} playerId - Player ID
 * @returns {string} WebSocket URL
 */
export const getWebSocketURL = (roomCode, playerId) => {
  const wsProtocol = BACKEND_URL.startsWith('https') ? 'wss' : 'ws';
  const baseURL = BACKEND_URL.replace(/^https?:\/\//, '');
  return `${wsProtocol}://${baseURL}/ws/${roomCode}/${playerId}`;
};

export default api;

