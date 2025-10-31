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
  const response = await api.get('/api/wallet/balance');
  return response.data;
};

/**
 * Request a cashout - UPDATED to V2 system
 * Uses per-transaction private HITs (no more "No HITs available" errors!)
 * @param {number} amountUsd - Amount in USD to cash out
 * @returns {Promise<Object>} Cashout transaction details with private HIT URL
 */
export const requestCashout = async (amountUsd) => {
  const response = await api.post('/api/wallet/cashout/v2', {
    amount_usd: amountUsd
  });
  return response.data;
};

/**
 * Check if MTurk HIT is ready for a transaction
 * @param {string} transactionId - Transaction UUID
 * @returns {Promise<Object>} Ready status {ready: boolean, message: string}
 */
export const checkHitReady = async (transactionId) => {
  const response = await api.get(`/api/wallet/cashout/${transactionId}/hit-ready`);
  return response.data;
};

/**
 * Get cashout transaction history
 * @returns {Promise<Object>} Transaction history
 */
export const getCashoutHistory = async () => {
  const response = await api.get('/api/wallet/cashout-history');
  return response.data;
};

/**
 * Get cashout transaction status
 * @param {string} transactionId - Transaction UUID
 * @returns {Promise<Object>} Transaction status
 */
export const getCashoutStatus = async (transactionId) => {
  const response = await api.get(`/api/wallet/cashout-status/${transactionId}`);
  return response.data;
};

/**
 * Update user's MTurk Worker ID
 * @param {string} workerId - MTurk Worker ID
 * @returns {Promise<Object>} Update result
 */
export const updateMTurkWorkerId = async (workerId) => {
  const response = await api.put('/api/profile/mturk-worker-id', {
    worker_id: workerId
  });
  return response.data;
};

/**
 * Get user profile with wallet information
 * @returns {Promise<Object>} User profile
 */
export const getUserProfile = async () => {
  const response = await api.get('/api/profile');
  return response.data;
};

/**
 * Cancel a pending cashout transaction
 * @param {string} transactionId - Transaction UUID to cancel
 * @returns {Promise<Object>} Cancellation result
 */
export const cancelCashout = async (transactionId) => {
  const response = await api.post(`/api/wallet/cashout-cancel/${transactionId}`);
  return response.data;
};

export default {
  getWalletBalance,
  requestCashout,
  checkHitReady,
  getCashoutHistory,
  getCashoutStatus,
  updateMTurkWorkerId,
  getUserProfile,
  cancelCashout
};

