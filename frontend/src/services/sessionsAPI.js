/**
 * Sessions API Service
 * Handles session-related API calls
 */

import api from './api';

export const sessionsAPI = {
  /**
   * List sessions for current user
   * @returns {Promise} List of sessions
   */
  listSessions: async () => {
    const response = await api.get('/api/sessions');
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
   * Claim a completion key
   * @param {string} completionKey - JWT completion key
   * @returns {Promise} Claim result
   */
  claimKey: async (completionKey) => {
    const response = await api.post('/api/sessions/claim', {
      completion_key: completionKey,
    });
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

  /**
   * Update payment status for a session (admin only)
   * @param {string} sessionId - Session UUID
   * @param {string} paymentStatus - 'pending' or 'paid'
   * @param {number} paymentAmount - Optional payment amount
   * @returns {Promise} Update result
   */
  updatePaymentStatus: async (sessionId, paymentStatus, paymentAmount = null) => {
    const response = await api.patch(`/api/admin/sessions/${sessionId}/payment`, {
      payment_status: paymentStatus,
      payment_amount: paymentAmount,
    });
    return response.data;
  },
};

export default sessionsAPI;

