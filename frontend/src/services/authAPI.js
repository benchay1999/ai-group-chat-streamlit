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
};

export default authAPI;

