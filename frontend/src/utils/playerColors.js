/**
 * Player Color Utility
 * Provides consistent color assignments for players across the application
 */

// Color palette with 8 distinct, accessible colors
// Each color has a gradient and text color optimized for WCAG AAA contrast
// Lighter gradients provide better readability for white text
const PLAYER_COLORS = [
  {
    // Blue - Softer, more readable
    gradient: 'from-blue-400 to-blue-500',
    text: 'text-white',
    textShadow: 'drop-shadow-md',
    senderText: 'text-blue-50',
    border: 'border-blue-400',
    bg: 'bg-blue-50',
  },
  {
    // Purple - Enhanced contrast
    gradient: 'from-purple-400 to-purple-500',
    text: 'text-white',
    textShadow: 'drop-shadow-md',
    senderText: 'text-purple-50',
    border: 'border-purple-400',
    bg: 'bg-purple-50',
  },
  {
    // Green - Eye-friendly
    gradient: 'from-emerald-400 to-emerald-500',
    text: 'text-white',
    textShadow: 'drop-shadow-md',
    senderText: 'text-emerald-50',
    border: 'border-emerald-400',
    bg: 'bg-emerald-50',
  },
  {
    // Orange - Warm and readable
    gradient: 'from-orange-400 to-orange-500',
    text: 'text-white',
    textShadow: 'drop-shadow-md',
    senderText: 'text-orange-50',
    border: 'border-orange-400',
    bg: 'bg-orange-50',
  },
  {
    // Pink - Vibrant yet soft
    gradient: 'from-pink-400 to-pink-500',
    text: 'text-white',
    textShadow: 'drop-shadow-md',
    senderText: 'text-pink-50',
    border: 'border-pink-400',
    bg: 'bg-pink-50',
  },
  {
    // Teal - Calming and clear
    gradient: 'from-teal-400 to-teal-500',
    text: 'text-white',
    textShadow: 'drop-shadow-md',
    senderText: 'text-teal-50',
    border: 'border-teal-400',
    bg: 'bg-teal-50',
  },
  {
    // Indigo - Deep and readable
    gradient: 'from-indigo-400 to-indigo-500',
    text: 'text-white',
    textShadow: 'drop-shadow-md',
    senderText: 'text-indigo-50',
    border: 'border-indigo-400',
    bg: 'bg-indigo-50',
  },
  {
    // Rose - Softer red alternative
    gradient: 'from-rose-400 to-rose-500',
    text: 'text-white',
    textShadow: 'drop-shadow-md',
    senderText: 'text-rose-50',
    border: 'border-rose-400',
    bg: 'bg-rose-50',
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

