/**
 * PlayerList Component
 * Enhanced player sidebar with voting capabilities
 */

import { useState, useEffect } from 'react';
import { useLanguage } from '../contexts/LanguageContext';

const PlayerList = ({ players, phase, castVote, currentPlayerId, onLeave, numHumanPlayers = 1 }) => {
  const { t } = useLanguage();
  const [selectedPlayers, setSelectedPlayers] = useState([]);
  const currentPlayer = players.find(p => p.id === currentPlayerId);
  const hasVoted = currentPlayer?.voted || false;
  
  // Use the num_human_players from backend (passed as prop)
  const numHumans = numHumanPlayers;
  
  // Combined voted check: server state only
  const isVotingDisabled = hasVoted;
  
  // For multi-human games, need to select N-1 players
  const votesNeeded = numHumans > 1 ? numHumans - 1 : 1;
  const canSubmitVotes = selectedPlayers.length === votesNeeded && !isVotingDisabled;
  
  // Toggle player selection
  const togglePlayerSelection = (playerId) => {
    if (isVotingDisabled) return;
    
    setSelectedPlayers(prev => {
      if (prev.includes(playerId)) {
        return prev.filter(id => id !== playerId);
      } else {
        // Only allow selecting up to votesNeeded players
        if (prev.length < votesNeeded) {
          return [...prev, playerId];
        }
        return prev;
      }
    });
  };
  
  // Submit votes
  const handleSubmitVotes = () => {
    if (canSubmitVotes && !isVotingDisabled) {
      // Always send array for consistency (backend handles both formats)
      castVote(selectedPlayers);
      setSelectedPlayers([]);
    }
  };
  
  // Reset selection when phase changes
  useEffect(() => {
    if (phase !== 'Voting') {
      setSelectedPlayers([]);
    }
  }, [phase]);

  return (
    <div className="w-80 bg-gradient-to-b from-gray-50 to-gray-100 border-r border-gray-200 flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">{t('player.players')}</h2>
        <p className="text-sm text-gray-600">
          {players.filter(p => !p.eliminated).length} / {players.length} {t('player.active')}
        </p>
      </div>

      {/* Player List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {players.map(player => {
          const isCurrentPlayer = player.id === currentPlayerId;
          const canSelect = phase === 'Voting' && !player.eliminated && !isCurrentPlayer && !isVotingDisabled;
          const isSelected = selectedPlayers.includes(player.id);

          return (
            <div
              key={player.id}
              onClick={() => canSelect && togglePlayerSelection(player.id)}
              className={`rounded-lg p-4 transition-all ${
                player.eliminated 
                  ? 'bg-gray-200 opacity-50' 
                  : isCurrentPlayer
                  ? 'bg-gradient-to-r from-blue-100 to-purple-100 border-2 border-blue-300'
                  : isSelected
                  ? 'bg-gradient-to-r from-green-100 to-emerald-100 border-2 border-green-400'
                  : 'bg-white shadow-sm hover:shadow-md'
              } ${canSelect ? 'cursor-pointer' : ''}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {/* Selection Checkbox for Multi-Human Voting */}
                  {canSelect && numHumans > 1 && (
                    <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                      isSelected ? 'bg-green-500 border-green-500' : 'border-gray-400'
                    }`}>
                      {isSelected && <span className="text-white text-xs">✓</span>}
                    </div>
                  )}
                  
                  <div className={`w-3 h-3 rounded-full ${
                    player.eliminated ? 'bg-gray-400' : 'bg-green-400'
                  }`}></div>
                  <span className={`font-semibold ${
                    player.eliminated ? 'text-gray-500 line-through' : 'text-gray-800'
                  }`}>
                    {player.id}
                  </span>
                  {isCurrentPlayer && (
                    <span className="text-xs bg-blue-500 text-white px-2 py-0.5 rounded-full">
                      {t('player.you')}
                    </span>
                  )}
                </div>

                {/* Status Badges */}
                <div className="flex items-center gap-2">
                  {(player.voted || (isCurrentPlayer && isVotingDisabled)) && phase !== 'Voting' && (
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-semibold">
                      ✓ {t('player.voted')}
                    </span>
                  )}
                  {player.eliminated && (
                    <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-full font-semibold">
                      {t('player.eliminated')}
                    </span>
                  )}
                </div>
              </div>

              {/* Single Vote Button (for single-human games only) */}
              {canSelect && numHumans === 1 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    castVote([player.id]);  // Send as array for consistency
                  }}
                  className="mt-3 w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white py-2 px-4 rounded-lg font-semibold hover:from-blue-600 hover:to-indigo-700 transition-all transform hover:scale-105"
                >
                  {t('player.voteButton')}
                </button>
              )}
            </div>
          );
        })}
      </div>
      
      {/* Submit Votes Button (for multi-human games) */}
      {phase === 'Voting' && !isVotingDisabled && numHumans > 1 && (
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <div className="mb-2 text-sm text-gray-600 text-center">
            {selectedPlayers.length < votesNeeded ? (
              <span>Select {votesNeeded - selectedPlayers.length} more player{votesNeeded - selectedPlayers.length !== 1 ? 's' : ''}</span>
            ) : (
              <span className="text-green-600 font-semibold">✓ Ready to submit votes</span>
            )}
          </div>
          <button
            onClick={handleSubmitVotes}
            disabled={!canSubmitVotes}
            className={`w-full py-3 px-4 rounded-lg font-bold transition-all ${
              canSubmitVotes
                ? 'bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:from-green-600 hover:to-emerald-700 transform hover:scale-105'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            Submit Votes ({selectedPlayers.length}/{votesNeeded})
          </button>
        </div>
      )}

      {/* Leave Button */}
      {onLeave && (
        <div className="p-4 border-t border-gray-200">
          <button
            onClick={onLeave}
            className="w-full bg-red-500 text-white py-2 px-4 rounded-lg font-semibold hover:bg-red-600 transition-colors"
          >
            {t('player.leaveRoom')}
          </button>
        </div>
      )}
    </div>
  );
};

export default PlayerList;
