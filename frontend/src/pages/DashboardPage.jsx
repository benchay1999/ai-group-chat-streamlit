/**
 * User Dashboard Page - Play-to-Earn Edition
 * Crypto/fintech inspired earnings-focused dashboard
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { sessionsAPI } from '../services/sessionsAPI';
import { format } from 'date-fns';
import { 
  Copy, Check, ExternalLink, Key, DollarSign, Clock, 
  TrendingUp, Zap, Star, Sparkles, Award
} from 'lucide-react';
import toast from 'react-hot-toast';
import axios from '../services/api';
import EarningsCounter from '../components/EarningsCounter';
import EarningsChart from '../components/EarningsChart';

const DashboardPage = () => {
  const { user, logout } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [earnings, setEarnings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [earningsLoading, setEarningsLoading] = useState(true);
  const [claimKey, setClaimKey] = useState('');
  const [claiming, setClaiming] = useState(false);
  const [copiedKey, setCopiedKey] = useState(null);

  useEffect(() => {
    loadSessions();
    loadEarnings();
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

  const loadEarnings = async () => {
    try {
      setEarningsLoading(true);
      const response = await axios.get('/api/users/earnings');
      setEarnings(response.data);
    } catch (error) {
      console.error('Failed to load earnings:', error);
    } finally {
      setEarningsLoading(false);
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
      loadSessions();
      loadEarnings();
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
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      {/* Header */}
      <div className="bg-gray-900 border-b border-gray-800 shadow-xl">
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
                className="px-4 py-2 bg-gray-800 text-white rounded-lg font-medium hover:bg-gray-700 transition-colors border border-gray-700"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Earnings Hero Section */}
      {earnings && !earningsLoading && (
        <div className="relative overflow-hidden bg-gradient-to-br from-gray-900 via-purple-900 to-black border-b border-gray-800">
          {/* Animated grid background */}
          <div className="absolute inset-0 bg-grid-pattern opacity-10" />
          
          {/* Main earnings display */}
          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <div className="text-center mb-8">
              <div className="flex items-center justify-center gap-2 mb-3">
                <Sparkles className="w-5 h-5 text-cyan-400" />
                <p className="text-sm text-cyan-400 font-mono tracking-wider uppercase">
                  Total Lifetime Earnings
                </p>
                <Sparkles className="w-5 h-5 text-cyan-400" />
              </div>
              
              <div className="mb-6">
                <div className="text-8xl font-black text-transparent bg-clip-text bg-gradient-to-r from-green-400 via-cyan-400 to-blue-500 animate-glow inline-block">
                  <EarningsCounter 
                    target={earnings.total_lifetime_earnings} 
                    duration={2500}
                    className="text-8xl font-black"
                    glowColor="green"
                  />
                </div>
              </div>
              
              <p className="text-xl text-gray-300 mb-2">
                From <span className="text-white font-semibold">{earnings.total_games}</span> games played
              </p>
              
              {earnings.tier && (
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-gray-800 bg-opacity-50 rounded-full border border-gray-700">
                  <Award className="w-5 h-5" style={{ color: earnings.tier.color }} />
                  <span className="text-sm font-semibold" style={{ color: earnings.tier.color }}>
                    {earnings.tier.name} Tier
                  </span>
                  {earnings.tier.next_threshold && (
                    <span className="text-xs text-gray-400">
                      (${(earnings.tier.next_threshold - earnings.total_lifetime_earnings).toFixed(2)} to next)
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Secondary stats row */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              {/* Pending Earnings */}
              <div className="bg-gray-800 bg-opacity-50 backdrop-blur-sm rounded-xl p-6 border border-gray-700 animate-pulse-yellow">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-400 font-medium">Pending</span>
                  <Clock className="w-5 h-5 text-yellow-500" />
                </div>
                <div className="text-3xl font-bold text-yellow-400">
                  <EarningsCounter 
                    target={earnings.pending_earnings} 
                    glowColor="yellow"
                  />
                </div>
              </div>

              {/* Last Game */}
              <div className="bg-gray-800 bg-opacity-50 backdrop-blur-sm rounded-xl p-6 border border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-400 font-medium">Last Game</span>
                  <Zap className="w-5 h-5 text-blue-500" />
                </div>
                <div className="text-3xl font-bold text-blue-400">
                  {earnings.recent_sessions.length > 0 && earnings.recent_sessions[0].amount > 0 ? (
                    <EarningsCounter 
                      target={earnings.recent_sessions[0].amount} 
                      glowColor="blue"
                    />
                  ) : (
                    <span className="text-gray-500">$0.00</span>
                  )}
                </div>
              </div>

              {/* Average Per Game */}
              <div className="bg-gray-800 bg-opacity-50 backdrop-blur-sm rounded-xl p-6 border border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-400 font-medium">Avg/Game</span>
                  <TrendingUp className="w-5 h-5 text-purple-500" />
                </div>
                <div className="text-3xl font-bold text-purple-400">
                  <EarningsCounter 
                    target={earnings.average_per_game} 
                    glowColor="purple"
                  />
                </div>
              </div>

              {/* This Week */}
              <div className="bg-gray-800 bg-opacity-50 backdrop-blur-sm rounded-xl p-6 border border-gray-700 animate-pulse-glow">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-400 font-medium">This Week</span>
                  <Star className="w-5 h-5 text-green-500" />
                </div>
                <div className="text-3xl font-bold text-green-400">
                  <EarningsCounter 
                    target={earnings.earnings_this_week} 
                    glowColor="green"
                  />
                </div>
              </div>
            </div>

            {/* Earnings Chart */}
            {earnings.recent_sessions.length > 0 && (
              <div className="bg-gray-800 bg-opacity-30 backdrop-blur-sm rounded-xl p-6 border border-gray-700 mb-8">
                <h3 className="text-lg font-semibold text-white mb-4">Recent Earnings Trend</h3>
                <EarningsChart data={earnings.recent_sessions.slice(0, 10).reverse()} />
              </div>
            )}

            {/* Call to Action */}
            <div className="text-center">
              <Link
                to="/lobby"
                className="inline-flex items-center gap-3 px-10 py-5 bg-gradient-to-r from-green-500 via-cyan-500 to-blue-500 text-white rounded-xl font-bold text-xl hover:from-green-600 hover:via-cyan-600 hover:to-blue-600 transition-all transform hover:scale-105 shadow-2xl animate-pulse-glow"
              >
                <DollarSign className="w-6 h-6" />
                Earn More
                <Sparkles className="w-6 h-6" />
              </Link>
              <p className="text-sm text-gray-400 mt-3">
                Play games to increase your earnings
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Claim Completion Key Section */}
        <div className="bg-gray-800 rounded-xl shadow-2xl p-6 mb-8 border border-gray-700">
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
              className="flex-1 px-4 py-3 bg-gray-900 text-white border border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            />
            <button
              type="submit"
              disabled={claiming || !claimKey.trim()}
              className="px-6 py-3 bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-lg font-medium hover:from-cyan-700 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {claiming ? 'Claiming...' : 'Claim Key'}
            </button>
          </form>
        </div>

        {/* Sessions List */}
        <div className="bg-gray-800 rounded-xl shadow-2xl overflow-hidden border border-gray-700">
          <div className="px-6 py-4 border-b border-gray-700 bg-gray-900">
            <h2 className="text-2xl font-bold text-white">Your Sessions</h2>
            <p className="text-gray-400 mt-1">View your game history and earnings</p>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500"></div>
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-12">
              <DollarSign className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400 text-lg mb-4">No sessions yet</p>
              <Link
                to="/lobby"
                className="inline-block px-6 py-3 bg-gradient-to-r from-green-600 to-cyan-600 text-white rounded-lg font-medium hover:from-green-700 hover:to-cyan-700 transition-colors"
              >
                Play Your First Game
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-900">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                      Room Code
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                      Earnings
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                      Language
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                      Players
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                      Completion Key
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
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
                        <div className="flex flex-col gap-1">
                          {session.payment_amount ? (
                            <div className="flex items-center gap-2">
                              <span
                                className={`text-lg font-bold ${
                                  session.payment_status === 'paid'
                                    ? 'text-green-400'
                                    : 'text-yellow-400'
                                }`}
                              >
                                ${session.payment_amount}
                              </span>
                              <span
                                className={`px-2 py-0.5 text-xs font-medium rounded ${
                                  session.payment_status === 'paid'
                                    ? 'bg-green-900 text-green-200'
                                    : 'bg-yellow-900 text-yellow-200 animate-pulse-yellow'
                                }`}
                              >
                                {session.payment_status}
                              </span>
                            </div>
                          ) : session.calculated_earnings ? (
                            <span className="text-sm text-gray-500">
                              Suggested: ${session.calculated_earnings}
                            </span>
                          ) : (
                            <span className="text-sm text-gray-500">Pending review</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center text-sm text-gray-400">
                          <Clock className="w-4 h-4 mr-2 text-gray-600" />
                          {format(new Date(session.completed_at), 'MMM d, yyyy HH:mm')}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-1 text-xs font-medium bg-gray-700 text-gray-300 rounded capitalize">
                          {session.language}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                        {session.num_human_players}/{session.total_players}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <code className="text-xs text-gray-500 bg-gray-900 px-2 py-1 rounded max-w-xs truncate">
                            {session.completion_key.substring(0, 20)}...
                          </code>
                          <button
                            onClick={() => copyToClipboard(session.completion_key, session.id)}
                            className="p-1 text-gray-500 hover:text-cyan-400 transition-colors"
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
                          className="inline-flex items-center gap-1 text-cyan-400 hover:text-cyan-300 font-medium transition-colors"
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
