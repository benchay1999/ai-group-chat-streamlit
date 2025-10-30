/**
 * MTurk API Service
 * Handles MTurk-specific API calls for admin payment management
 */

import api from './api';

export const mturkAPI = {
  /**
   * Approve MTurk payment for a session
   * @param {string} sessionId - Session ID
   * @returns {Promise} Payment result
   */
  approvePayment: async (sessionId) => {
    const response = await api.post(`/api/admin/mturk/sessions/${sessionId}/approve-payment`);
    return response.data;
  },

  /**
   * Create a new MTurk HIT
   * @param {Object} hitConfig - HIT configuration
   * @returns {Promise} HIT creation result
   */
  createHIT: async (hitConfig) => {
    const response = await api.post('/api/admin/mturk/create-hit', hitConfig);
    return response.data;
  },

  /**
   * List active MTurk HITs
   * @returns {Promise} List of active HITs
   */
  listHITs: async () => {
    const response = await api.get('/api/admin/mturk/hits');
    return response.data;
  },

  /**
   * Get MTurk account balance
   * @returns {Promise} Account balance
   */
  getBalance: async () => {
    const response = await api.get('/api/admin/mturk/balance');
    return response.data;
  },
};

export default mturkAPI;

