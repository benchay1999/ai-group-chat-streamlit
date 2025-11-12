/**
 * Player Color Utility
 * Provides consistent color assignments for players across the application
 */

// Color palette with 8 distinct, accessible colors
// Each color has a gradient and text color optimized for WCAG AA contrast
const PLAYER_COLORS = [
  {
    // Blue
    gradient: 'from-blue-500 to-blue-600',
    text: 'text-white',
    textLight: 'text-blue-100',
    border: 'border-blue-500',
    bg: 'bg-blue-50',
  },
  {
    // Purple
    gradient: 'from-purple-500 to-purple-600',
    text: 'text-white',
    textLight: 'text-purple-100',
    border: 'border-purple-500',
    bg: 'bg-purple-50',
  },
  {
    // Green
    gradient: 'from-green-500 to-green-600',
    text: 'text-white',
    textLight: 'text-green-100',
    border: 'border-green-500',
    bg: 'bg-green-50',
  },
  {
    // Orange
    gradient: 'from-orange-500 to-orange-600',
    text: 'text-white',
    textLight: 'text-orange-100',
    border: 'border-orange-500',
    bg: 'bg-orange-50',
  },
  {
    // Pink
    gradient: 'from-pink-500 to-pink-600',
    text: 'text-white',
    textLight: 'text-pink-100',
    border: 'border-pink-500',
    bg: 'bg-pink-50',
  },
  {
    // Teal
    gradient: 'from-teal-500 to-teal-600',
    text: 'text-white',
    textLight: 'text-teal-100',
    border: 'border-teal-500',
    bg: 'bg-teal-50',
  },
  {
    // Indigo
    gradient: 'from-indigo-500 to-indigo-600',
    text: 'text-white',
    textLight: 'text-indigo-100',
    border: 'border-indigo-500',
    bg: 'bg-indigo-50',
  },
  {
    // Red
    gradient: 'from-red-500 to-red-600',
    text: 'text-white',
    textLight: 'text-red-100',
    border: 'border-red-500',
    bg: 'bg-red-50',
  },
];

/**
 * Extract player number from player ID
 * @param {string} playerId - Player ID (e.g., "Player 1", "Player 2", "AI_1")
 * @returns {number} - Player number (1-based)
 */
const extractPlayerNumber = (playerId) => {
  if (!playerId) return 0;
  
  // Match "Player N" format
  const match = playerId.match(/Player\s+(\d+)/i);
  if (match) {
    return parseInt(match[1], 10);
  }
  
  // Match "AI_N" format
  const aiMatch = playerId.match(/AI_(\d+)/i);
  if (aiMatch) {
    return parseInt(aiMatch[1], 10);
  }
  
  // Fallback: hash the player ID for consistency
  let hash = 0;
  for (let i = 0; i < playerId.length; i++) {
    hash = ((hash << 5) - hash) + playerId.charCodeAt(i);
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash);
};

/**
 * Get color scheme for a player
 * @param {string} playerId - Player ID
 * @returns {object} Color scheme with gradient, text, and border classes
 */
export const getPlayerColor = (playerId) => {
  const playerNumber = extractPlayerNumber(playerId);
  const colorIndex = (playerNumber - 1) % PLAYER_COLORS.length;
  return PLAYER_COLORS[colorIndex];
};

/**
 * Get all available colors (useful for previews or legends)
 * @returns {array} Array of all color schemes
 */
export const getAllColors = () => {
  return PLAYER_COLORS;
};

