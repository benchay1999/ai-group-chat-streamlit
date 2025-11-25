/**
 * Leaderboard API Service
 * Handles leaderboard data fetching
 */

import api from './api';

/**
 * Get the leaderboard of top users by gems earned
 * @param {number} limit - Number of top users to fetch (default: 10)
 * @returns {Promise<Object>} Leaderboard data with user rankings
 */
export const getLeaderboard = async (limit = 10) => {
  try {
    const response = await api.get('/api/leaderboard', {
      params: { limit }
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch leaderboard:', error);
    throw error;
  }
};

export default {
  getLeaderboard
};

