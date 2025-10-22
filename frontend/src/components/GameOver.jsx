/**
 * GameOver Component
 * Displays game over screen with results
 */

const GameOver = ({ winner, suspect, suspectRole, voteCountsDisplay, onLeave }) => {
  const isHumanWin = winner === 'human';

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-8 animate-fade-in">
        {/* Winner Banner */}
        <div className={`text-center mb-6 p-6 rounded-xl ${
          isHumanWin 
            ? 'bg-gradient-to-r from-green-400 to-emerald-500' 
            : 'bg-gradient-to-r from-red-400 to-rose-500'
        }`}>
          <h2 className="text-4xl font-bold text-white mb-2">
            {isHumanWin ? '🎉 Humans Win!' : '🤖 AI Wins!'}
          </h2>
          <p className="text-white text-lg opacity-90">
            {isHumanWin 
              ? 'The humans successfully identified an AI!' 
              : 'The AIs caught the human!'}
          </p>
        </div>

        {/* Suspect Info */}
        {suspect && (
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <h3 className="text-sm font-semibold text-gray-600 mb-2">Suspected Player</h3>
            <div className="flex items-center justify-between">
              <span className="text-xl font-bold text-gray-800">{suspect}</span>
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                suspectRole === 'human' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'bg-purple-100 text-purple-700'
              }`}>
                {suspectRole === 'human' ? '👤 Human' : '🤖 AI'}
              </span>
            </div>
          </div>
        )}

        {/* Vote Counts */}
        {voteCountsDisplay && voteCountsDisplay.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-600 mb-3">Vote Results</h3>
            <div className="space-y-2">
              {voteCountsDisplay.map(({ player, votes }) => (
                <div key={player} className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
                  <span className="font-semibold text-gray-800">{player}</span>
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      {[...Array(votes)].map((_, i) => (
                        <span key={i} className="text-red-500">●</span>
                      ))}
                    </div>
                    <span className="text-sm font-bold text-gray-600">{votes}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Button */}
        <button
          onClick={onLeave}
          className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 transition-all transform hover:scale-105"
        >
          Back to Lobby
        </button>
      </div>
    </div>
  );
};

export default GameOver;

