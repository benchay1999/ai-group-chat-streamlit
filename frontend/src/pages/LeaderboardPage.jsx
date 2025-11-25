/**
 * LeaderboardPage.jsx
 * Displays the top users by total gems earned
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getLeaderboard } from '../services/leaderboardAPI';
import { ArrowLeft, Trophy, Gem, Star, Target, TrendingUp } from 'lucide-react';
import toast from 'react-hot-toast';

const LeaderboardPage = () => {
  const navigate = useNavigate();
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLeaderboard();
    
    // Auto-refresh every 60 seconds
    const interval = setInterval(() => {
      fetchLeaderboard();
    }, 60000);
    
    return () => clearInterval(interval);
  }, []);

  const fetchLeaderboard = async () => {
    try {
      setLoading(true);
      const data = await getLeaderboard(10);
      setLeaderboard(data.leaderboard || []);
    } catch (error) {
      console.error('Failed to fetch leaderboard:', error);
      toast.error('Failed to load leaderboard');
    } finally {
      setLoading(false);
    }
  };

  const getRankBadge = (rank) => {
    switch (rank) {
      case 1:
        return { emoji: '🥇', color: 'from-yellow-400 to-yellow-600', glow: 'shadow-yellow-500/50' };
      case 2:
        return { emoji: '🥈', color: 'from-gray-300 to-gray-500', glow: 'shadow-gray-400/50' };
      case 3:
        return { emoji: '🥉', color: 'from-orange-400 to-orange-600', glow: 'shadow-orange-500/50' };
      default:
        return { emoji: `#${rank}`, color: 'from-purple-400 to-purple-600', glow: 'shadow-purple-500/30' };
    }
  };

  if (loading && leaderboard.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading leaderboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50 py-8 px-4">
      <div className="max-w-5xl mx-auto">
        
        {/* Back Button */}
        <button
          onClick={() => navigate('/lobby')}
          className="mb-6 flex items-center gap-2 text-gray-600 hover:text-gray-900 transition"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Lobby
        </button>

        {/* Header */}
        <div className="bg-white rounded-xl shadow-lg p-8 mb-6">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-full flex items-center justify-center shadow-lg">
              <Trophy className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-4xl font-bold text-gray-900">Leaderboard</h1>
              <p className="text-gray-600">Top players by total gems earned</p>
            </div>
          </div>
          
          {/* Stats Banner */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <div className="flex items-center gap-2 text-purple-700 mb-1">
                <Trophy className="w-4 h-4" />
                <span className="text-sm font-semibold">Total Players</span>
              </div>
              <p className="text-2xl font-bold text-purple-900">{leaderboard.length}</p>
            </div>
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-center gap-2 text-yellow-700 mb-1">
                <Gem className="w-4 h-4" />
                <span className="text-sm font-semibold">Top Earner</span>
              </div>
              <p className="text-2xl font-bold text-yellow-900">
                {leaderboard.length > 0 ? leaderboard[0].total_gems_earned.toLocaleString() : 0} gems
              </p>
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center gap-2 text-blue-700 mb-1">
                <TrendingUp className="w-4 h-4" />
                <span className="text-sm font-semibold">Competition</span>
              </div>
              <p className="text-2xl font-bold text-blue-900">Active</p>
            </div>
          </div>
        </div>

        {/* Empty State */}
        {leaderboard.length === 0 && !loading && (
          <div className="bg-white rounded-xl shadow-lg p-12 text-center">
            <Trophy className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">No Players Yet</h2>
            <p className="text-gray-600">Be the first to earn gems and claim the top spot!</p>
          </div>
        )}

        {/* Leaderboard Table */}
        {leaderboard.length > 0 && (
          <div className="bg-white rounded-xl shadow-lg overflow-hidden">
            {/* Desktop Table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gradient-to-r from-purple-600 to-blue-600 text-white">
                  <tr>
                    <th className="px-6 py-4 text-left font-semibold">Rank</th>
                    <th className="px-6 py-4 text-left font-semibold">Player</th>
                    <th className="px-6 py-4 text-left font-semibold">Total Gems</th>
                    <th className="px-6 py-4 text-left font-semibold">Games Played</th>
                    <th className="px-6 py-4 text-left font-semibold">Win Rate</th>
                    <th className="px-6 py-4 text-left font-semibold">Level</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {leaderboard.map((player) => {
                    const badge = getRankBadge(player.rank);
                    return (
                      <tr 
                        key={player.rank}
                        className={`hover:bg-gray-50 transition ${
                          player.rank <= 3 ? 'bg-gradient-to-r bg-opacity-5 ' + (
                            player.rank === 1 ? 'from-yellow-100 to-yellow-50' :
                            player.rank === 2 ? 'from-gray-100 to-gray-50' :
                            'from-orange-100 to-orange-50'
                          ) : ''
                        }`}
                      >
                        {/* Rank */}
                        <td className="px-6 py-4">
                          <div className={`inline-flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-br ${badge.color} text-white font-bold shadow-lg ${badge.glow}`}>
                            {badge.emoji}
                          </div>
                        </td>
                        
                        {/* Player Name */}
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-gray-900">{player.user_id}</span>
                            {player.rank === 1 && <Trophy className="w-4 h-4 text-yellow-500" />}
                          </div>
                        </td>
                        
                        {/* Total Gems */}
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <Gem className="w-5 h-5 text-purple-600" />
                            <span className="font-bold text-purple-900">
                              {player.total_gems_earned.toLocaleString()}
                            </span>
                          </div>
                        </td>
                        
                        {/* Games Played */}
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <Target className="w-4 h-4 text-blue-600" />
                            <span className="text-gray-700">{player.total_games}</span>
                          </div>
                        </td>
                        
                        {/* Win Rate */}
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <Star className="w-4 h-4 text-green-600" />
                                <span className="font-semibold text-green-700">
                                  {player.win_rate}%
                                </span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                                <div 
                                  className="bg-gradient-to-r from-green-400 to-green-600 h-2 rounded-full transition-all"
                                  style={{ width: `${Math.min(player.win_rate, 100)}%` }}
                                ></div>
                              </div>
                            </div>
                          </div>
                        </td>
                        
                        {/* Level */}
                        <td className="px-6 py-4">
                          <div className="inline-flex items-center gap-1 px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full font-semibold">
                            <Star className="w-4 h-4" />
                            {player.level}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards */}
            <div className="md:hidden divide-y divide-gray-200">
              {leaderboard.map((player) => {
                const badge = getRankBadge(player.rank);
                return (
                  <div 
                    key={player.rank}
                    className={`p-4 ${
                      player.rank <= 3 ? 'bg-gradient-to-r bg-opacity-5 ' + (
                        player.rank === 1 ? 'from-yellow-100 to-yellow-50' :
                        player.rank === 2 ? 'from-gray-100 to-gray-50' :
                        'from-orange-100 to-orange-50'
                      ) : ''
                    }`}
                  >
                    {/* Rank and Name */}
                    <div className="flex items-center gap-4 mb-3">
                      <div className={`flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-br ${badge.color} text-white font-bold shadow-lg ${badge.glow}`}>
                        {badge.emoji}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-gray-900">{player.user_id}</span>
                          {player.rank === 1 && <Trophy className="w-4 h-4 text-yellow-500" />}
                        </div>
                        <div className="inline-flex items-center gap-1 px-2 py-0.5 bg-indigo-100 text-indigo-800 rounded-full text-xs font-semibold mt-1">
                          <Star className="w-3 h-3" />
                          Level {player.level}
                        </div>
                      </div>
                    </div>
                    
                    {/* Stats Grid */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-purple-50 rounded-lg p-3">
                        <div className="flex items-center gap-1 text-xs text-purple-700 mb-1">
                          <Gem className="w-3 h-3" />
                          <span>Total Gems</span>
                        </div>
                        <p className="font-bold text-purple-900">{player.total_gems_earned.toLocaleString()}</p>
                      </div>
                      
                      <div className="bg-blue-50 rounded-lg p-3">
                        <div className="flex items-center gap-1 text-xs text-blue-700 mb-1">
                          <Target className="w-3 h-3" />
                          <span>Games</span>
                        </div>
                        <p className="font-bold text-blue-900">{player.total_games}</p>
                      </div>
                      
                      <div className="bg-green-50 rounded-lg p-3 col-span-2">
                        <div className="flex items-center gap-1 text-xs text-green-700 mb-1">
                          <Star className="w-3 h-3" />
                          <span>Win Rate</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1">
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div 
                                className="bg-gradient-to-r from-green-400 to-green-600 h-2 rounded-full transition-all"
                                style={{ width: `${Math.min(player.win_rate, 100)}%` }}
                              ></div>
                            </div>
                          </div>
                          <span className="font-bold text-green-700">{player.win_rate}%</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Footer Info */}
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800">
            <strong>💡 Tip:</strong> Play more games and win to climb the leaderboard! The leaderboard updates every 60 seconds.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LeaderboardPage;

