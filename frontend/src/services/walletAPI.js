/**
 * Wallet API Service
 * Handles gem wallet and cashout operations
 */

import api from './api';

/**
 * Get wallet balance and statistics
 * @returns {Promise<Object>} Wallet data
 */
export const getWalletBalance = async () => {
  const response = await api.get('/wallet/balance');
  return response.data;
};

/**
 * Request a cashout
 * @param {number} amountUsd - Amount in USD to cash out
 * @returns {Promise<Object>} Cashout transaction details
 */
export const requestCashout = async (amountUsd) => {
  const response = await api.post('/wallet/cashout', {
    amount_usd: amountUsd
  });
  return response.data;
};

/**
 * Get cashout transaction history
 * @returns {Promise<Object>} Transaction history
 */
export const getCashoutHistory = async () => {
  const response = await api.get('/wallet/cashout-history');
  return response.data;
};

/**
 * Get cashout transaction status
 * @param {string} transactionId - Transaction UUID
 * @returns {Promise<Object>} Transaction status
 */
export const getCashoutStatus = async (transactionId) => {
  const response = await api.get(`/wallet/cashout-status/${transactionId}`);
  return response.data;
};

/**
 * Update user's MTurk Worker ID
 * @param {string} workerId - MTurk Worker ID
 * @returns {Promise<Object>} Update result
 */
export const updateMTurkWorkerId = async (workerId) => {
  const response = await api.put('/profile/mturk-worker-id', {
    worker_id: workerId
  });
  return response.data;
};

/**
 * Get user profile with wallet information
 * @returns {Promise<Object>} User profile
 */
export const getUserProfile = async () => {
  const response = await api.get('/profile');
  return response.data;
};

export default {
  getWalletBalance,
  requestCashout,
  getCashoutHistory,
  getCashoutStatus,
  updateMTurkWorkerId,
  getUserProfile
};

