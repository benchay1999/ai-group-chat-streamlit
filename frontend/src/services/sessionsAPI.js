/**
 * Sessions API Service
 * Handles session-related API calls
 */

import api from './api';

export const sessionsAPI = {
  /**
   * List sessions for current user
   * @param {Object} params - Query parameters for filtering (Admin only)
   * @returns {Promise} List of sessions
   */
  listSessions: async (params = {}) => {
    const response = await api.get('/api/sessions', { params });
    return response.data;
  },

  /**
   * Get detailed session information
   * @param {string} sessionId - Session UUID
   * @returns {Promise} Detailed session data including chat history
   */
  getSessionDetail: async (sessionId) => {
    const response = await api.get(`/api/sessions/${sessionId}`);
    return response.data;
  },

  /**
   * Get admin dashboard statistics
   * @returns {Promise} Dashboard stats
   */
  getAdminDashboard: async () => {
    const response = await api.get('/api/admin/dashboard');
    return response.data;
  },
};

export default sessionsAPI;

