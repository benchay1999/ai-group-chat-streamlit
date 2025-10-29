/**
 * User Dashboard Page
 * Shows user's gamification stats, sessions, completion keys, and payment status
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { sessionsAPI } from '../services/sessionsAPI';
import { format } from 'date-fns';
import { 
  Copy, Check, ExternalLink, Key, DollarSign, Clock, 
  Trophy, Target, Zap, TrendingUp, Award, Star
} from 'lucide-react';
import toast from 'react-hot-toast';
import axios from '../services/api';
import ProgressBar from '../components/ProgressBar';
import StatsCard from '../components/StatsCard';

const DashboardPage = () => {
  const { user, logout } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [userStats, setUserStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [claimKey, setClaimKey] = useState('');
  const [claiming, setClaiming] = useState(false);
  const [copiedKey, setCopiedKey] = useState(null);

  useEffect(() => {
    loadSessions();
    loadUserStats();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await sessionsAPI.listSessions();
      setSessions(data.sessions);
    } catch (error) {
      toast.error('Failed to load sessions');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const loadUserStats = async () => {
    try {
      setStatsLoading(true);
      const response = await axios.get('/api/users/stats');
      setUserStats(response.data);
    } catch (error) {
      console.error('Failed to load user stats:', error);
      // Don't show error toast - gamification is optional
    } finally {
      setStatsLoading(false);
    }
  };

  const handleClaimKey = async (e) => {
    e.preventDefault();
    if (!claimKey.trim()) return;

    try {
      setClaiming(true);
      await sessionsAPI.claimKey(claimKey);
      toast.success('Completion key claimed successfully!');
      setClaimKey('');
      loadSessions(); // Reload sessions
      loadUserStats(); // Reload stats
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to claim key';
      toast.error(message);
    } finally {
      setClaiming(false);
    }
  };

  const copyToClipboard = (text, sessionId) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(sessionId);
    toast.success('Copied to clipboard!');
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900">
      {/* Header */}
      <div className="bg-gray-800 shadow-lg border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white">Dashboard</h1>
              <p className="text-gray-400 mt-1">Welcome back, {user?.user_id}</p>
            </div>
            <div className="flex items-center gap-4">
              {user?.role === 'admin' && (
                <>
                  <Link
                    to="/admin"
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-colors"
                  >
                    Admin Panel
                  </Link>
                  <Link
                    to="/admin/analytics"
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
                  >
                    Analytics
                  </Link>
                </>
              )}
              <button
                onClick={logout}
                className="px-4 py-2 bg-gray-700 text-white rounded-lg font-medium hover:bg-gray-600 transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Gamification Hero Section */}
        {userStats && !statsLoading && (
          <div className="mb-8">
            {/* Level & Points Card */}
            <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg p-8 shadow-xl mb-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-6">
                  <div className="bg-white bg-opacity-20 rounded-full w-24 h-24 flex items-center justify-center backdrop-blur-sm">
                    <span className="text-5xl font-bold text-white">{userStats.level}</span>
                  </div>
                  <div>
                    <h2 className="text-3xl font-bold text-white mb-1">Level {userStats.level}</h2>
                    <p className="text-xl text-purple-100">{userStats.total_points.toLocaleString()} Points</p>
                    {userStats.streak.current > 0 && (
                      <div className="flex items-center gap-2 mt-2">
                        <Zap className="text-yellow-300" size={20} />
                        <span className="text-yellow-200 font-semibold">
                          {userStats.streak.current} day streak! 🔥
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-purple-100 text-sm mb-1">Next Level</div>
                  <div className="text-2xl font-bold text-white">{userStats.points_for_next_level.toLocaleString()}</div>
                  <div className="text-purple-200 text-sm mt-1">
                    {userStats.level_progress.current.toLocaleString()} / {userStats.level_progress.needed.toLocaleString()}
                  </div>
                </div>
              </div>
              
              {/* Progress Bar */}
              <div className="mt-6">
                <ProgressBar
                  current={userStats.level_progress.current}
                  max={userStats.level_progress.needed}
                  label="Progress to Next Level"
                  color="yellow"
                  showPercentage={true}
                />
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
              <StatsCard
                title="Games Played"
                value={userStats.games.total}
                subtitle={`${userStats.games.wins} wins`}
                icon="🎮"
                color="blue"
              />
              <StatsCard
                title="Win Rate"
                value={`${userStats.games.win_rate}%`}
                subtitle={`${userStats.games.losses} losses`}
                icon="🎯"
                color="green"
              />
              <StatsCard
                title="Current Streak"
                value={`${userStats.streak.current} days`}
                subtitle={`Best: ${userStats.streak.longest} days`}
                icon="🔥"
                color="yellow"
              />
              <StatsCard
                title="Achievements"
                value={`${userStats.achievements.unlocked_count}/${userStats.achievements.total_count}`}
                subtitle="Unlocked"
                icon="🏆"
                color="purple"
              />
            </div>

            {/* Motivational Message & Next Achievements */}
            {userStats.motivational_message && (
              <div className="bg-gradient-to-r from-green-500 to-emerald-600 rounded-lg p-6 mb-6 shadow-lg">
                <div className="flex items-center gap-3">
                  <Target className="text-white" size={32} />
                  <div>
                    <h3 className="text-xl font-bold text-white mb-1">Keep Going!</h3>
                    <p className="text-green-50">{userStats.motivational_message}</p>
                  </div>
                </div>
                
                {/* Next Achievements Preview */}
                {userStats.next_achievements && userStats.next_achievements.length > 0 && (
                  <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
                    {userStats.next_achievements.map((achievement) => (
                      <div key={achievement.id} className="bg-white bg-opacity-20 rounded-lg p-3 backdrop-blur-sm">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-2xl">{achievement.icon}</span>
                          <span className="font-semibold text-white text-sm">{achievement.name}</span>
                        </div>
                        <p className="text-xs text-green-100">{achievement.description}</p>
                        <div className="mt-2 text-xs text-yellow-200 font-semibold">
                          +{achievement.points} pts • {achievement.progress_needed} more needed
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Call to Action */}
            <div className="text-center">
              <Link
                to="/lobby"
                className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg font-bold text-lg hover:from-purple-700 hover:to-pink-700 transition-all transform hover:scale-105 shadow-lg"
              >
                <Star className="animate-pulse" size={24} />
                Play Another Game
                <TrendingUp size={24} />
              </Link>
            </div>
          </div>
        )}

        {/* Claim Completion Key Section */}
        <div className="bg-gray-800 rounded-lg shadow-xl p-6 mb-8">
          <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
            <Key className="text-yellow-500" />
            Claim Completion Key
          </h2>
          <p className="text-gray-400 mb-4">
            Enter a completion key from a game you played to claim it to your account
          </p>
          <form onSubmit={handleClaimKey} className="flex gap-3">
            <input
              type="text"
              value={claimKey}
              onChange={(e) => setClaimKey(e.target.value)}
              placeholder="Paste your completion key here..."
              className="flex-1 px-4 py-3 bg-gray-700 text-white border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
            <button
              type="submit"
              disabled={claiming || !claimKey.trim()}
              className="px-6 py-3 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {claiming ? 'Claiming...' : 'Claim Key'}
            </button>
          </form>
        </div>

        {/* Sessions List */}
        <div className="bg-gray-800 rounded-lg shadow-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-700">
            <h2 className="text-2xl font-bold text-white">Your Sessions</h2>
            <p className="text-gray-400 mt-1">View your game history and completion keys</p>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-400 text-lg mb-4">No sessions yet</p>
              <Link
                to="/lobby"
                className="inline-block px-6 py-3 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-colors"
              >
                Play Your First Game
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Room Code
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Language
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Players
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Payment
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Completion Key
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {sessions.map((session) => (
                    <tr key={session.id} className="hover:bg-gray-750 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm font-mono font-medium text-white">
                          {session.room_code}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center text-sm text-gray-300">
                          <Clock className="w-4 h-4 mr-2 text-gray-500" />
                          {format(new Date(session.completed_at), 'MMM d, yyyy HH:mm')}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-1 text-xs font-medium bg-gray-700 text-gray-300 rounded capitalize">
                          {session.language}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                        {session.num_human_players}/{session.total_players}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-1 text-xs font-medium rounded ${
                              session.payment_status === 'paid'
                                ? 'bg-green-900 text-green-200'
                                : 'bg-yellow-900 text-yellow-200'
                            }`}
                          >
                            {session.payment_status}
                          </span>
                          {session.payment_amount && (
                            <span className="text-sm text-gray-400 flex items-center">
                              <DollarSign className="w-4 h-4" />
                              {session.payment_amount}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <code className="text-xs text-gray-400 bg-gray-900 px-2 py-1 rounded max-w-xs truncate">
                            {session.completion_key.substring(0, 20)}...
                          </code>
                          <button
                            onClick={() => copyToClipboard(session.completion_key, session.id)}
                            className="p-1 text-gray-400 hover:text-white transition-colors"
                            title="Copy completion key"
                          >
                            {copiedKey === session.id ? (
                              <Check className="w-4 h-4 text-green-500" />
                            ) : (
                              <Copy className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                        <Link
                          to={`/sessions/${session.id}`}
                          className="inline-flex items-center gap-1 text-purple-400 hover:text-purple-300 font-medium transition-colors"
                        >
                          View Details
                          <ExternalLink className="w-4 h-4" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
