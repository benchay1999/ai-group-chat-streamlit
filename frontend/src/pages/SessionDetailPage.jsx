/**
 * Session Detail Page
 * Shows detailed session information with chat history and voting visualization
 */

import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { sessionsAPI } from '../services/sessionsAPI';
import { format } from 'date-fns';
import { ArrowLeft, Users, MessageCircle, Trophy } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import toast from 'react-hot-toast';
import { getPlayerColor } from '../utils/playerColors';
import { useAuth } from '../contexts/AuthContext';

const SessionDetailPage = () => {
  const { sessionId } = useParams();
  const { user } = useAuth();
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSession();
  }, [sessionId]);

  const loadSession = async () => {
    try {
      setLoading(true);
      const data = await sessionsAPI.getSessionDetail(sessionId);
      setSession(data);
    } catch (error) {
      toast.error('Failed to load session details');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };


  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Session Not Found</h2>
          <Link to="/dashboard" className="text-blue-600 hover:underline">
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const stats = session.stats || {};
  const chatHistory = stats.chat_history || [];
  const votes = stats.votes || {};
  const voteCounts = stats.vote_counts || {};
  const players = stats.players || [];

  // Prepare display history with gem summary
  const displayHistory = [...chatHistory];
  
  // Inject Gem Summary if available
  if (session.gem_rewards && Object.keys(session.gem_rewards).length > 0) {
    const gemSummaryLines = Object.entries(session.gem_rewards).map(([pid, data]) => {
      // Support both new format (net_change) and old format (total_gems)
      const amount = data.net_change !== undefined ? data.net_change : (data.total_gems || 0);
      const sign = amount >= 0 ? '+' : '';
      const isWinner = data.is_winner ? '🏆 ' : '';
      return `${isWinner}${pid}: ${sign}${amount} gems`;
    });
    
    if (gemSummaryLines.length > 0) {
      const gemSummary = gemSummaryLines.join('\n');
      // Add as a special system message at the end
      displayHistory.push({
        sender: 'GAME OVER',
        message: `💎 REWARDS SUMMARY 💎\n\n${gemSummary}`,
        timestamp: session.completed_at ? new Date(session.completed_at).getTime() / 1000 : Date.now() / 1000,
        isSystemReward: true
      });
    }
  }

  // Prepare vote data for pie chart
  const voteData = Object.entries(voteCounts).map(([player, count]) => ({
    name: player,
    value: count,
  }));

  const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <Link
            to="/dashboard"
            className="inline-flex items-center text-sm font-medium text-gray-700 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">
            Session: {session.room_code}
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            {format(new Date(session.completed_at), 'MMMM d, yyyy HH:mm')}
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Session Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Language</p>
                <p className="text-2xl font-bold text-gray-900 capitalize">{session.language}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Players</p>
                <p className="text-2xl font-bold text-gray-900">
                  {session.num_human_players}/{session.total_players}
                </p>
              </div>
              <Users className="w-8 h-8 text-blue-600" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div className="w-full">
                <p className="text-sm font-medium text-gray-600 mb-1">Discussion</p>
                <p className="text-2xl font-bold text-gray-900">
                  {Math.floor(session.discussion_duration / 60)}m
                </p>
              </div>
              <MessageCircle className="w-8 h-8 text-green-600" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div className="w-full">
                <p className="text-sm font-medium text-gray-600 mb-1">Voting</p>
                <p className="text-2xl font-bold text-gray-900">
                  {Math.floor(session.voting_duration / 60)}m
                </p>
              </div>
              <MessageCircle className="w-8 h-8 text-purple-600" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div className="w-full">
                <p className="text-sm font-medium text-gray-600">Most Voted Player</p>
                <p className="text-2xl font-bold text-gray-900 mb-1">
                  {stats.selected_suspect || 'N/A'}
                </p>
                {stats.suspect_role && (
                  <p className="text-sm text-gray-600 capitalize">
                    ({stats.suspect_role})
                  </p>
                )}
              </div>
              <Trophy className="w-8 h-8 text-yellow-600" />
            </div>
          </div>
        </div>

        {/* Gem Reward Card with Breakdown */}
        {session.gem_earned !== null && session.gem_earned !== undefined && (
          <div className={`rounded-lg shadow p-6 mb-8 ${
            session.gem_earned >= 0 
              ? 'bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-300'
              : 'bg-gradient-to-r from-red-50 to-rose-50 border-2 border-red-300'
          }`}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600 mb-2">
                  {session.gem_earned >= 0 ? 'Gems Earned' : 'Gems Lost'}
                </p>
                <p className={`text-4xl font-bold ${
                  session.gem_earned >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {session.gem_earned >= 0 ? '+' : ''}{session.gem_earned} gems
                </p>
              </div>
              <div className={`w-16 h-16 rounded-full flex items-center justify-center ${
                session.gem_earned >= 0 ? 'bg-green-200' : 'bg-red-200'
              }`}>
                <span className="text-3xl">{session.gem_earned >= 0 ? '💎' : '💔'}</span>
              </div>
            </div>
            
            {/* Breakdown if available */}
            {session.gem_breakdown && (
              <div className="bg-white bg-opacity-60 rounded-lg p-4 space-y-2 mt-3">
                <p className="text-xs font-semibold text-gray-600 uppercase mb-2">Breakdown</p>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-700">Base Reward:</span>
                  <span className="text-green-700 font-bold">+{session.gem_breakdown.base_gems} gems</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-700">Stakes Won/Lost:</span>
                  <span className={`font-bold ${session.gem_breakdown.stake_gems >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                    {session.gem_breakdown.stake_gems >= 0 ? '+' : ''}{session.gem_breakdown.stake_gems} gems
                  </span>
                </div>
                <div className="border-t-2 border-gray-300 pt-2 flex items-center justify-between font-bold">
                  <span className="text-gray-800">Net Change:</span>
                  <span className={session.gem_breakdown.net_change >= 0 ? 'text-green-600' : 'text-red-600'}>
                    {session.gem_breakdown.net_change >= 0 ? '+' : ''}{session.gem_breakdown.net_change} gems
                  </span>
                </div>
              </div>
            )}
            
            <p className="text-sm text-gray-600 mt-3">
              {session.gem_earned >= 0 
                ? 'You won this game!' 
                : 'Stakes lost in this game'}
            </p>
          </div>
        )}

        {/* Player Identification Card */}
        {session.current_user_player_id && (
          <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-6 mb-8">
            <div className="flex items-center gap-3">
              <div className="bg-blue-600 text-white rounded-full w-12 h-12 flex items-center justify-center font-bold text-lg">
                👤
              </div>
              <div>
                <h2 className="text-xl font-bold text-blue-900">You were {session.current_user_player_id}</h2>
                <p className="text-sm text-blue-700">This was your player identity in this session</p>
              </div>
            </div>
          </div>
        )}

        {/* Player Mappings Card (Admin only) */}
        {user?.role === 'admin' && session.player_mappings && session.player_mappings.some(p => p.user_name) && (
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Player Identities (Admin View)</h2>
            <div className="space-y-2">
              {session.player_mappings.map((mapping) => (
                <div key={mapping.player_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      mapping.role === 'human' 
                        ? 'bg-green-100 text-green-800'
                        : 'bg-purple-100 text-purple-800'
                    }`}>
                      {mapping.role === 'human' ? '👤 Human' : '🤖 AI'}
                    </span>
                    <span className="font-semibold text-gray-900">{mapping.player_id}</span>
                  </div>
                  <div>
                    {mapping.user_name ? (
                      <span className="text-sm text-gray-700">
                        User: <span className="font-mono font-medium">{mapping.user_name}</span>
                      </span>
                    ) : (
                      <span className="text-sm text-gray-500 italic">Not logged in</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Player List */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Players</h2>
            <div className="space-y-2">
              {players.map((player) => {
                const isCurrentUser = session.current_user_player_id === player.id;
                return (
                  <div
                    key={player.id}
                    className={`flex items-center justify-between p-3 rounded-lg transition-all ${
                      isCurrentUser
                        ? 'bg-blue-100 border-2 border-blue-400 shadow-md'
                        : 'bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className={`font-medium ${isCurrentUser ? 'text-blue-900' : 'text-gray-900'}`}>
                        {player.id}
                      </span>
                      {isCurrentUser && (
                        <span className="px-2 py-1 bg-blue-600 text-white text-xs font-bold rounded-full">
                          YOU
                        </span>
                      )}
                    </div>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${
                        player.role === 'human'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-purple-100 text-purple-800'
                      }`}
                    >
                      {player.role === 'human' ? 'Human' : 'AI'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Voting Results */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Voting Results</h2>
            {voteData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={voteData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name}: ${value}`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {voteData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-500 text-center">No voting data available</p>
            )}
            
            <div className="mt-4 pt-4 border-t border-gray-200">
              <p className="text-sm font-medium text-gray-700 mb-2">Vote Details:</p>
              <div className="space-y-1">
                {Object.entries(votes).map(([voter, target]) => {
                  // Handle both list votes (multi-human) and single votes
                  const targets = Array.isArray(target) ? target : [target];
                  return (
                    <div key={voter} className="text-sm text-gray-600">
                      <span className="font-medium">{voter}</span> voted for{' '}
                      <span className="font-medium">{targets.join(', ')}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Chat History */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Chat History</h2>
          <div className="space-y-3 max-h-[600px] overflow-y-auto">
            {displayHistory.length > 0 ? (
              displayHistory.map((msg, index) => {
                // Handle special system reward message
                if (msg.isSystemReward) {
                  return (
                    <div key={index} className="p-4 rounded-lg bg-gradient-to-r from-gray-900 to-gray-800 border-l-4 border-yellow-400 shadow-md my-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-bold text-yellow-400 text-sm uppercase tracking-wide flex items-center gap-2">
                          <Trophy className="w-4 h-4" />
                          {msg.sender}
                        </span>
                        <span className="text-xs text-gray-400 font-medium">
                          {format(new Date(msg.timestamp * 1000), 'HH:mm:ss')}
                        </span>
                      </div>
                      <pre className="text-white font-medium leading-relaxed whitespace-pre-wrap font-mono text-sm">
                        {msg.message}
                      </pre>
                    </div>
                  );
                }

                const playerColor = getPlayerColor(msg.sender);
                
                return (
                  <div
                    key={index}
                    className={`p-4 rounded-lg ${playerColor.bg} border-l-4 ${playerColor.border} shadow-sm hover:shadow-md transition-shadow`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-gray-900 text-sm uppercase tracking-wide">{msg.sender}</span>
                      <span className="text-xs text-gray-500 font-medium">
                        {format(new Date(msg.timestamp * 1000), 'HH:mm:ss')}
                      </span>
                    </div>
                    <p className="text-gray-800 font-medium leading-relaxed">{msg.message}</p>
                  </div>
                );
              })
            ) : (
              <p className="text-gray-500 text-center py-8">No chat history available</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SessionDetailPage;

