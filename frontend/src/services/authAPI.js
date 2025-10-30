/**
 * Authentication API Service
 * Handles auth-related API calls
 */

import api from './api';

export const authAPI = {
  /**
   * Register a new user
   * @param {string} userId - User identifier
   * @param {string} password - Password
   * @returns {Promise} Registration result
   */
  register: async (userId, password) => {
    const response = await api.post('/api/auth/register', {
      user_id: userId,
      password: password,
    });
    return response.data;
  },

  /**
   * Login user and get JWT token
   * @param {string} userId - User identifier
   * @param {string} password - Password
   * @returns {Promise} Login result with access_token
   */
  login: async (userId, password) => {
    const response = await api.post('/api/auth/login', {
      user_id: userId,
      password: password,
    });
    return response.data;
  },

  /**
   * Get current user information
   * @returns {Promise} Current user data
   */
  getCurrentUser: async () => {
    const response = await api.get('/api/auth/me');
    return response.data;
  },

  /**
   * Register or login MTurk worker (auto-registration)
   * @param {string} workerId - MTurk worker ID
   * @param {string} assignmentId - MTurk assignment ID
   * @param {string} hitId - MTurk HIT ID
   * @returns {Promise} Auth result with access_token and mturk_context
   */
  mturkRegister: async (workerId, assignmentId, hitId) => {
    const response = await api.post('/api/auth/mturk-register', {
      worker_id: workerId,
      assignment_id: assignmentId,
      hit_id: hitId,
    });
    return response.data;
  },
};

export default authAPI;

