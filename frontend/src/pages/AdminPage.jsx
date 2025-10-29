/**
 * Admin Panel Page
 * Manage all sessions and update payment status
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { sessionsAPI } from '../services/sessionsAPI';
import { format } from 'date-fns';
import { DollarSign, Clock, CheckCircle, Users, ArrowLeft } from 'lucide-react';
import toast from 'react-hot-toast';

const AdminPage = () => {
  const { logout } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updatingSession, setUpdatingSession] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [sessionsData, dashboardData] = await Promise.all([
        sessionsAPI.listSessions(),
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

  const handleUpdatePayment = async (sessionId, newStatus, amount = null) => {
    try {
      setUpdatingSession(sessionId);
      await sessionsAPI.updatePaymentStatus(sessionId, newStatus, amount);
      toast.success('Payment status updated successfully');
      loadData(); // Reload data
    } catch (error) {
      toast.error('Failed to update payment status');
      console.error(error);
    } finally {
      setUpdatingSession(null);
    }
  };

  const promptPaymentAmount = (sessionId, currentStatus, suggestedAmount = null) => {
    const defaultValue = suggestedAmount ? suggestedAmount.toFixed(2) : '';
    const amount = prompt(`Enter payment amount:${suggestedAmount ? ` (Suggested: $${suggestedAmount.toFixed(2)})` : ''}`, defaultValue);
    if (amount !== null) {
      const parsedAmount = parseFloat(amount);
      if (!isNaN(parsedAmount) && parsedAmount >= 0) {
        handleUpdatePayment(sessionId, currentStatus, parsedAmount);
      } else {
        toast.error('Invalid amount');
      }
    }
  };

  const acceptSuggestedAmount = (sessionId, currentStatus, suggestedAmount) => {
    handleUpdatePayment(sessionId, currentStatus, suggestedAmount);
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
                    <tr key={session.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {session.room_code}
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
                          {session.payment_status === 'pending' ? (
                            <button
                              onClick={() => handleUpdatePayment(session.id, 'paid')}
                              disabled={updatingSession === session.id}
                              className="px-3 py-1 bg-green-600 text-white rounded text-xs font-medium hover:bg-green-700 disabled:opacity-50"
                            >
                              {updatingSession === session.id ? 'Updating...' : 'Mark Paid'}
                            </button>
                          ) : (
                            <button
                              onClick={() => handleUpdatePayment(session.id, 'pending')}
                              disabled={updatingSession === session.id}
                              className="px-3 py-1 bg-yellow-600 text-white rounded text-xs font-medium hover:bg-yellow-700 disabled:opacity-50"
                            >
                              {updatingSession === session.id ? 'Updating...' : 'Mark Pending'}
                            </button>
                          )}
                          {session.calculated_earnings && !session.payment_amount && (
                            <button
                              onClick={() => acceptSuggestedAmount(session.id, session.payment_status, session.calculated_earnings)}
                              disabled={updatingSession === session.id}
                              className="px-3 py-1 bg-cyan-600 text-white rounded text-xs font-medium hover:bg-cyan-700 disabled:opacity-50"
                            >
                              Accept ${session.calculated_earnings}
                            </button>
                          )}
                          <button
                            onClick={() => promptPaymentAmount(session.id, session.payment_status, session.calculated_earnings)}
                            disabled={updatingSession === session.id}
                            className="px-3 py-1 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
                          >
                            Set Amount
                          </button>
                        </div>
                        <div>
                          <Link
                            to={`/sessions/${session.id}`}
                            className="text-purple-600 hover:text-purple-900 font-medium text-xs"
                          >
                            View Details →
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

