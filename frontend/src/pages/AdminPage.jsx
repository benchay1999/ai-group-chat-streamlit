/**
 * Admin Panel Page
 * Manage all sessions and update payment status
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { sessionsAPI } from '../services/sessionsAPI';
import { mturkAPI } from '../services/mturkAPI';
import { format } from 'date-fns';
import { DollarSign, Clock, CheckCircle, Users, ArrowLeft, Zap, Award, ExternalLink, Search, Filter, X } from 'lucide-react';
import toast from 'react-hot-toast';

const AdminPage = () => {
  const { logout } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updatingSession, setUpdatingSession] = useState(null);
  
  // Filter State
  const [filters, setFilters] = useState({
    participant_name: '',
    winner_name: '',
    language: '',
    discussion_duration: '',
    voting_duration: '',
    num_human_players: '',
    total_players: '',
    sort_by: ''
  });

  useEffect(() => {
    loadData();
  }, []);

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  const applyFilters = () => {
    loadData();
  };
  
  const clearFilters = () => {
    setFilters({
      participant_name: '',
      winner_name: '',
      language: '',
      discussion_duration: '',
      voting_duration: '',
      num_human_players: '',
      total_players: '',
      sort_by: ''
    });
    // Trigger reload after state update (using a timeout or effect would be better, 
    // but calling loadData with empty object works for immediate action)
    setTimeout(() => {
       // We need to pass empty filters manually or wait for state. 
       // Since loadData reads state, let's just trigger it.
       // Ideally loadData should accept optional params to override state, 
       // but reading state is fine if we wait for next tick or use explicit clear.
    }, 0);
    // Actually, better to just reload with cleared object
    loadData({
      participant_name: '',
      winner_name: '',
      language: '',
      discussion_duration: '',
      voting_duration: '',
      num_human_players: '',
      total_players: '',
      sort_by: ''
    });
  };

  const loadData = async (overrideFilters = null) => {
    try {
      setLoading(true);
      
      // Use overrideFilters if provided (for clear button), otherwise use state
      const currentFilters = overrideFilters || filters;
      
      // Remove empty filters
      const activeFilters = {};
      Object.keys(currentFilters).forEach(key => {
        if (currentFilters[key]) activeFilters[key] = currentFilters[key];
      });

      const [sessionsData, dashboardData] = await Promise.all([
        sessionsAPI.listSessions(activeFilters),
        sessionsAPI.getAdminDashboard(),
      ]);
      setSessions(sessionsData.sessions);
      setStats(dashboardData);
    } catch (error) {
      toast.error('Failed to load admin data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleMTurkPayment = async (sessionId) => {
    if (!confirm('This will trigger the MTurk API to approve the assignment and send bonus. Continue?')) {
      return;
    }
    
    try {
      setUpdatingSession(sessionId);
      const result = await mturkAPI.approvePayment(sessionId);
      
      if (result.success) {
        toast.success(`✅ MTurk payment processed! Base: $${result.base_pay}, Bonus: $${result.bonus_amount || 0}`);
        loadData(); // Reload data
      } else {
        toast.error(result.error || 'Payment failed');
      }
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to process MTurk payment';
      toast.error(message);
      console.error(error);
    } finally {
      setUpdatingSession(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="text-3xl font-bold">Admin Panel</h1>
              <p className="text-purple-100">Manage sessions and payments</p>
            </div>
            <div className="flex items-center gap-4">
              <Link
                to="/dashboard"
                className="px-4 py-2 text-sm font-medium text-white hover:text-purple-100"
              >
                <ArrowLeft className="w-4 h-4 inline mr-2" />
                Dashboard
              </Link>
              <button
                onClick={logout}
                className="px-4 py-2 text-sm font-medium text-white hover:text-purple-100"
              >
                Logout
              </button>
            </div>
          </div>

          {/* Stats Cards */}
          {stats && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-purple-100 text-sm">Total Sessions</p>
                    <p className="text-3xl font-bold">{stats.total_sessions}</p>
                  </div>
                  <Users className="w-8 h-8 text-purple-200" />
                </div>
              </div>

              <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-purple-100 text-sm">Pending Payments</p>
                    <p className="text-3xl font-bold">{stats.pending_payments}</p>
                  </div>
                  <Clock className="w-8 h-8 text-yellow-300" />
                </div>
              </div>

              <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-purple-100 text-sm">Paid Sessions</p>
                    <p className="text-3xl font-bold">{stats.paid_sessions}</p>
                  </div>
                  <CheckCircle className="w-8 h-8 text-green-300" />
                </div>
              </div>

              <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-purple-100 text-sm">Unclaimed</p>
                    <p className="text-3xl font-bold">{stats.unclaimed_sessions}</p>
                  </div>
                  <DollarSign className="w-8 h-8 text-red-300" />
                </div>
              </div>
            </div>
          )}
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters Section */}
        <div className="bg-white rounded-lg shadow-lg mb-8 p-6">
          <div className="flex items-center gap-2 mb-4 text-gray-800">
            <Filter className="w-5 h-5" />
            <h2 className="text-lg font-semibold">Filter Sessions</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Participant Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Participant Name</label>
              <input
                type="text"
                name="participant_name"
                value={filters.participant_name}
                onChange={handleFilterChange}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm p-2 border"
                placeholder="Search user..."
              />
            </div>
            
            {/* Winner Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Winner Name</label>
              <input
                type="text"
                name="winner_name"
                value={filters.winner_name}
                onChange={handleFilterChange}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm p-2 border"
                placeholder="Search winner..."
              />
            </div>

            {/* Language */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Language</label>
              <select
                name="language"
                value={filters.language}
                onChange={handleFilterChange}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm p-2 border"
              >
                <option value="">Any Language</option>
                <option value="english">English</option>
                <option value="chinese">Chinese</option>
                <option value="korean">Korean</option>
                <option value="spanish">Spanish</option>
                <option value="japanese">Japanese</option>
              </select>
            </div>

            {/* Sort By */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sort By</label>
              <select
                name="sort_by"
                value={filters.sort_by}
                onChange={handleFilterChange}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm p-2 border"
              >
                <option value="">Most Recent</option>
                <option value="highest_reward">Highest Reward</option>
              </select>
            </div>

            {/* Discussion Duration */}
            <div>
               <label className="block text-sm font-medium text-gray-700 mb-1">Discussion Duration</label>
               <select
                  name="discussion_duration"
                  value={filters.discussion_duration}
                  onChange={handleFilterChange}
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm p-2 border"
               >
                 <option value="">Any Duration</option>
                 <option value="60">Debug (60s)</option>
                 <option value="300">5 Minutes (300s)</option>
                 <option value="420">7 Minutes (420s)</option>
                 <option value="600">10 Minutes (600s)</option>
               </select>
            </div>

             {/* Num Human Players */}
             <div>
               <label className="block text-sm font-medium text-gray-700 mb-1">Human Players</label>
               <select
                  name="num_human_players"
                  value={filters.num_human_players}
                  onChange={handleFilterChange}
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm p-2 border"
               >
                 <option value="">Any</option>
                 <option value="1">1 Player</option>
                 <option value="2">2 Players</option>
                 <option value="3">3 Players</option>
                 <option value="4">4 Players</option>
                 <option value="5">5 Players</option>
               </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button
              onClick={clearFilters}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-2"
            >
              <X className="w-4 h-4" />
              Clear
            </button>
            <button
              onClick={applyFilters}
              className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700 flex items-center gap-2"
            >
              <Search className="w-4 h-4" />
              Apply Filters
            </button>
          </div>
        </div>

        {/* Sessions Table */}
        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
            <h2 className="text-lg font-semibold text-gray-900">All Sessions</h2>
          </div>

          {loading ? (
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto"></div>
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <p>No sessions yet.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Room Code
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Worker
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Language
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Players
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Completed
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Payment Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Amount
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {sessions.map((session) => (
                    <tr key={session.id} className={`hover:bg-gray-50 ${session.mturk_worker_id ? 'bg-yellow-50' : ''}`}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {session.room_code}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {session.mturk_worker_id ? (
                          <div className="flex items-center gap-2">
                            <Award className="w-4 h-4 text-yellow-600" />
                            <div>
                              <div className="font-medium text-gray-900 text-xs">
                                {session.mturk_worker_id.substring(0, 10)}...
                              </div>
                              {session.mturk_assignment_id && (
                                <div className="text-xs text-gray-500">
                                  {session.mturk_assignment_id.substring(0, 10)}...
                                </div>
                              )}
                            </div>
                          </div>
                        ) : (
                          <span className="text-gray-400 text-xs">Regular user</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">
                        {session.language}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {session.num_human_players}/{session.total_players}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {format(new Date(session.completed_at), 'MMM d, HH:mm')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex flex-col gap-1">
                          {session.payment_status === 'paid' ? (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              <CheckCircle className="w-3 h-3 mr-1" />
                              Paid
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                              <Clock className="w-3 h-3 mr-1" />
                              Pending
                            </span>
                          )}
                          {session.mturk_worker_id && (
                            <div className="flex gap-1">
                              {session.mturk_payment_sent ? (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-green-50 text-green-700 border border-green-200">
                                  ✓ Base
                                </span>
                              ) : null}
                              {session.mturk_bonus_sent ? (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-green-50 text-green-700 border border-green-200">
                                  ✓ Bonus
                                </span>
                              ) : null}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex flex-col gap-1">
                          <span className="text-sm text-gray-900 font-medium">
                            {session.payment_amount ? `$${session.payment_amount}` : '-'}
                          </span>
                          {session.calculated_earnings && (
                            <span className={`text-xs ${
                              session.payment_amount && 
                              Math.abs(session.payment_amount - session.calculated_earnings) > 0.01
                                ? 'text-orange-600 font-medium'
                                : 'text-gray-500'
                            }`}>
                              Suggested: ${session.calculated_earnings}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm space-y-1">
                        <div className="flex gap-2 flex-wrap">
                          {/* MTurk Auto-Payment Button (Legacy - for sessions with MTurk integration) */}
                          {session.mturk_worker_id && !session.mturk_payment_sent && session.calculated_earnings && (
                            <button
                              onClick={() => handleMTurkPayment(session.id)}
                              disabled={updatingSession === session.id}
                              className="px-3 py-1 bg-gradient-to-r from-yellow-500 to-orange-500 text-white rounded text-xs font-bold hover:from-yellow-600 hover:to-orange-600 disabled:opacity-50 flex items-center gap-1 shadow-md"
                            >
                              <Zap className="w-3 h-3" />
                              {updatingSession === session.id ? 'Processing...' : `MTurk Pay $${session.calculated_earnings}`}
                            </button>
                          )}
                          
                          {/* Note: "Mark Paid" and "Set Amount" buttons removed */}
                          {/* Payments are now handled through the gem economy system */}
                          {/* See /wallet for cashout functionality */}
                        </div>
                        <div>
                          <Link
                            to={`/sessions/${session.id}`}
                            className="text-purple-600 hover:text-purple-900 font-medium text-xs flex items-center gap-1"
                          >
                            View Details <ExternalLink className="w-3 h-3" />
                          </Link>
                        </div>
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

export default AdminPage;

