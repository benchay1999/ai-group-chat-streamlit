/**
 * PlayerList Component
 * Enhanced player sidebar with voting capabilities
 */

const PlayerList = ({ players, phase, castVote, currentPlayerId, onLeave }) => {
  const currentPlayer = players.find(p => p.id === currentPlayerId);
  const hasVoted = currentPlayer?.voted || false;

  return (
    <div className="w-80 bg-gradient-to-b from-gray-50 to-gray-100 border-r border-gray-200 flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">Players</h2>
        <p className="text-sm text-gray-600">
          {players.filter(p => !p.eliminated).length} / {players.length} active
        </p>
      </div>

      {/* Player List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {players.map(player => {
          const isCurrentPlayer = player.id === currentPlayerId;
          const canVote = phase === 'Voting' && !player.eliminated && !isCurrentPlayer && !hasVoted;

          return (
            <div
              key={player.id}
              className={`rounded-lg p-4 transition-all ${
                player.eliminated 
                  ? 'bg-gray-200 opacity-50' 
                  : isCurrentPlayer
                  ? 'bg-gradient-to-r from-blue-100 to-purple-100 border-2 border-blue-300'
                  : 'bg-white shadow-sm hover:shadow-md'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
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
                      You
                    </span>
                  )}
                </div>

                {/* Status Badges */}
                <div className="flex items-center gap-2">
                  {player.voted && (
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-semibold">
                      ✓ Voted
                    </span>
                  )}
                  {player.eliminated && (
                    <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-full font-semibold">
                      Eliminated
                    </span>
                  )}
                </div>
              </div>

              {/* Vote Button */}
              {canVote && (
                <button
                  onClick={() => castVote(player.id)}
                  className="mt-3 w-full bg-gradient-to-r from-red-500 to-rose-600 text-white py-2 px-4 rounded-lg font-semibold hover:from-red-600 hover:to-rose-700 transition-all transform hover:scale-105"
                >
                  Vote to Eliminate
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Leave Button */}
      {onLeave && (
        <div className="p-4 border-t border-gray-200">
          <button
            onClick={onLeave}
            className="w-full bg-red-500 text-white py-2 px-4 rounded-lg font-semibold hover:bg-red-600 transition-colors"
          >
            Leave Room
          </button>
        </div>
      )}
    </div>
  );
};

export default PlayerList;
