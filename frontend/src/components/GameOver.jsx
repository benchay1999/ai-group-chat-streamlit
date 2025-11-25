/**
 * GameOver Component
 * Displays game over screen with results and gamification rewards
 */

import { useState, useEffect } from 'react';
import { roomAPI } from '../services/api';
import PointsAnimation from './PointsAnimation';
import AchievementUnlock from './AchievementUnlock';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import { TrendingUp, Award, Zap } from 'lucide-react';

const GameOver = ({ winner, suspect, suspectRole, voteCountsDisplay, onLeave, roomCode }) => {
  const { user } = useAuth();
  const isHumanWin = winner === 'human';
  const [gamificationData, setGamificationData] = useState(null);
  const [showPoints, setShowPoints] = useState(false);
  const [showAchievements, setShowAchievements] = useState(false);

  useEffect(() => {
    // Fetch session stats which includes gamification data
    const fetchStats = async () => {
      try {
        const stats = await roomAPI.getGameState(roomCode, 'Player1');
        
        // Gamification data (only for logged-in users)
        if (stats.gamification && user) {
          setGamificationData(stats.gamification);
          
          // Show points animation after 1 second
          setTimeout(() => {
            setShowPoints(true);
          }, 1000);
          
          // Show achievements after points (if any)
          if (stats.gamification.new_achievements && stats.gamification.new_achievements.length > 0) {
            setTimeout(() => {
              setShowPoints(false);
              setShowAchievements(true);
            }, 4000);
          } else {
            // Hide points animation after showing
            setTimeout(() => {
              setShowPoints(false);
            }, 4000);
          }
        }
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      }
    };

    fetchStats();
  }, [roomCode, user]);

  const handleAchievementsClose = () => {
    setShowAchievements(false);
  };

  const handlePointsComplete = () => {
    setShowPoints(false);
  };

  return (
    <>
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
                ? 'The humans successfully identified the most human-like player!' 
                : 'The AIs tricked humans into voting for an AI!'}
            </p>
            {suspect && (
              <div className="mt-3 pt-3 border-t border-white border-opacity-30">
                <p className="text-white text-sm font-medium opacity-90 mb-1">
                  Most Voted Player:
                </p>
                <p className="text-white text-lg font-bold">
                  {suspect}
                </p>
              </div>
            )}
          </div>

          {/* Gamification Quick Stats (if available) */}
          {gamificationData && user && (
            <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-4 mb-6 border-2 border-purple-200">
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <div className="text-2xl font-bold text-purple-700">
                    +{gamificationData.points_earned}
                  </div>
                  <div className="text-xs text-purple-600 font-medium">Points Earned</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-blue-700 flex items-center justify-center gap-1">
                    <TrendingUp size={20} />
                    {gamificationData.user_stats.level}
                  </div>
                  <div className="text-xs text-blue-600 font-medium">Level</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-yellow-700 flex items-center justify-center gap-1">
                    <Zap size={20} />
                    {gamificationData.user_stats.current_streak}
                  </div>
                  <div className="text-xs text-yellow-600 font-medium">Day Streak</div>
                </div>
              </div>
              
              {gamificationData.new_achievements && gamificationData.new_achievements.length > 0 && (
                <div className="mt-3 text-center">
                  <div className="inline-flex items-center gap-2 bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-semibold">
                    <Award size={16} />
                    {gamificationData.new_achievements.length} New Achievement{gamificationData.new_achievements.length > 1 ? 's' : ''} Unlocked!
                  </div>
                </div>
              )}
            </div>
          )}

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

          {/* Action Buttons */}
          <div className="space-y-3">
            {user && (
              <button
                onClick={() => window.location.href = '/dashboard'}
                className="w-full px-6 py-3 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-all"
              >
                📊 View Dashboard & Stats
              </button>
            )}
            
            <button
              onClick={onLeave}
              className="w-full px-6 py-3 bg-gray-600 text-white rounded-lg font-semibold hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-all"
            >
              ← Back to Lobby
            </button>
          </div>
        </div>
      </div>

      {/* Points Animation */}
      {showPoints && gamificationData && (
        <div className="fixed inset-0 flex items-center justify-center z-[60] pointer-events-none">
          <div className="pointer-events-auto">
            <PointsAnimation
              points={gamificationData.points_earned}
              breakdown={gamificationData.points_breakdown}
              onComplete={handlePointsComplete}
            />
          </div>
        </div>
      )}

      {/* Achievement Unlock */}
      {showAchievements && gamificationData && gamificationData.new_achievements && (
        <AchievementUnlock
          achievements={gamificationData.new_achievements}
          onClose={handleAchievementsClose}
        />
      )}
    </>
  );
};

export default GameOver;
