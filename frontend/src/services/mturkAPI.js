/**
 * MTurk API Service
 * Handles MTurk-specific API calls for admin payment management
 */

import api from './api';

export const mturkAPI = {
  /**
   * Approve MTurk payment for a session (legacy sessions only)
   * @param {string} sessionId - Session ID
   * @returns {Promise} Payment result
   */
  approvePayment: async (sessionId) => {
    const response = await api.post(`/api/admin/mturk/sessions/${sessionId}/approve-payment`);
    return response.data;
  },
};

export default mturkAPI;

