/**
 * User Dashboard Page
 * Shows user's sessions, completion keys, and payment status
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { sessionsAPI } from '../services/sessionsAPI';
import { format } from 'date-fns';
import { Copy, Check, ExternalLink, Key, DollarSign, Clock } from 'lucide-react';
import toast from 'react-hot-toast';

const DashboardPage = () => {
  const { user, logout } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [claimKey, setClaimKey] = useState('');
  const [claiming, setClaiming] = useState(false);
  const [copiedKey, setCopiedKey] = useState(null);

  useEffect(() => {
    loadSessions();
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

  const handleClaimKey = async (e) => {
    e.preventDefault();
    if (!claimKey.trim()) return;

    try {
      setClaiming(true);
      await sessionsAPI.claimKey(claimKey);
      toast.success('Completion key claimed successfully!');
      setClaimKey('');
      loadSessions(); // Reload sessions
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

  const getPaymentBadge = (status) => {
    if (status === 'paid') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <Check className="w-3 h-3 mr-1" />
          Paid
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
        <Clock className="w-3 h-3 mr-1" />
        Pending
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-sm text-gray-600">Welcome back, {user?.user_id}</p>
          </div>
          <div className="flex items-center gap-4">
            <Link
              to="/lobby"
              className="px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              Play Game
            </Link>
            {user?.role === 'admin' && (
              <Link
                to="/admin"
                className="px-4 py-2 text-sm font-medium text-purple-600 hover:text-purple-700"
              >
                Admin Panel
              </Link>
            )}
            <button
              onClick={logout}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Claim Key Card */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Key className="w-5 h-5 mr-2 text-blue-600" />
            Claim Completion Key
          </h2>
          <form onSubmit={handleClaimKey} className="flex gap-3">
            <input
              type="text"
              value={claimKey}
              onChange={(e) => setClaimKey(e.target.value)}
              placeholder="Paste your completion key here..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={claiming}
            />
            <button
              type="submit"
              disabled={claiming || !claimKey.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {claiming ? 'Claiming...' : 'Claim'}
            </button>
          </form>
          <p className="mt-2 text-sm text-gray-500">
            If you received a completion key from another device or account, enter it here to claim it.
          </p>
        </div>

        {/* Sessions Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Sessions</p>
                <p className="text-3xl font-bold text-gray-900">{sessions.length}</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-full">
                <ExternalLink className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Pending Payment</p>
                <p className="text-3xl font-bold text-yellow-600">
                  {sessions.filter(s => s.payment_status === 'pending').length}
                </p>
              </div>
              <div className="p-3 bg-yellow-100 rounded-full">
                <Clock className="w-6 h-6 text-yellow-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Earned</p>
                <p className="text-3xl font-bold text-green-600">
                  ${sessions.reduce((sum, s) => sum + (s.payment_amount || 0), 0).toFixed(2)}
                </p>
              </div>
              <div className="p-3 bg-green-100 rounded-full">
                <DollarSign className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </div>
        </div>

        {/* Sessions List */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Your Sessions</h2>
          </div>

          {loading ? (
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <p className="mb-4">No sessions yet. Start playing to earn completion keys!</p>
              <Link
                to="/lobby"
                className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700"
              >
                Play Your First Game
              </Link>
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
                      Language
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Players
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Completed
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Payment
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Completion Key
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {sessions.map((session) => (
                    <tr key={session.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {session.room_code}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {session.language}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {session.num_human_players}/{session.total_players}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {format(new Date(session.completed_at), 'MMM d, yyyy HH:mm')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex flex-col gap-1">
                          {getPaymentBadge(session.payment_status)}
                          {session.payment_amount && (
                            <span className="text-sm font-medium text-gray-900">
                              ${session.payment_amount}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        <button
                          onClick={() => copyToClipboard(session.completion_key, session.id)}
                          className="flex items-center gap-2 px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                        >
                          {copiedKey === session.id ? (
                            <>
                              <Check className="w-3 h-3 text-green-600" />
                              Copied!
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" />
                              Copy Key
                            </>
                          )}
                        </button>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <Link
                          to={`/sessions/${session.id}`}
                          className="text-blue-600 hover:text-blue-900 font-medium"
                        >
                          View Details
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

