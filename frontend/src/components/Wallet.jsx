/**
 * Wallet Component
 * Displays gem balance, cashout options, and transaction history
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Gem, DollarSign, TrendingUp, History, AlertCircle, ExternalLink, Clock, X, ArrowLeft } from 'lucide-react';
import { getWalletBalance, getCashoutHistory, cancelCashout } from '../services/walletAPI';
import CashoutModal from './CashoutModal';

const Wallet = () => {
  const navigate = useNavigate();
  const [walletData, setWalletData] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCashoutModal, setShowCashoutModal] = useState(false);
  const [error, setError] = useState(null);
  const [cancellingTx, setCancellingTx] = useState(null);

  useEffect(() => {
    loadWalletData();
  }, []);

  const loadWalletData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [balance, history] = await Promise.all([
        getWalletBalance(),
        getCashoutHistory()
      ]);
      
      setWalletData(balance);
      setTransactions(history.transactions || []);
    } catch (err) {
      console.error('Error loading wallet data:', err);
      setError(err.response?.data?.detail || 'Failed to load wallet data');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      pending: { color: 'bg-yellow-100 text-yellow-800', text: 'Pending' },
      hit_created: { color: 'bg-blue-100 text-blue-800', text: 'HIT Created' },
      completed: { color: 'bg-green-100 text-green-800', text: 'Completed' },
      failed: { color: 'bg-red-100 text-red-800', text: 'Failed' },
      cancelled: { color: 'bg-gray-100 text-gray-800', text: 'Cancelled' }
    };
    
    const badge = badges[status] || badges.pending;
    
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${badge.color}`}>
        {badge.text}
      </span>
    );
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const handleCancelTransaction = async (transactionId, amountGems) => {
    // Confirm with user
    const confirmed = window.confirm(
      `Are you sure you want to cancel this cashout?\n\n` +
      `Amount: ${amountGems.toLocaleString()} gems will be returned to your wallet.`
    );
    
    if (!confirmed) return;
    
    try {
      setCancellingTx(transactionId);
      
      const result = await cancelCashout(transactionId);
      
      // Show success message
      alert(
        `✅ Transaction Cancelled\n\n` +
        `${result.gems_returned.toLocaleString()} gems have been returned to your wallet.\n` +
        `New Balance: ${result.new_balance.toLocaleString()} gems`
      );
      
      // Reload wallet data
      await loadWalletData();
      
    } catch (err) {
      console.error('Error cancelling transaction:', err);
      const errorMsg = err.response?.data?.detail || 'Failed to cancel transaction';
      alert(`❌ Error: ${errorMsg}`);
    } finally {
      setCancellingTx(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading wallet...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <AlertCircle className="w-12 h-12 text-red-600 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-red-800 mb-2 text-center">Error Loading Wallet</h2>
          <p className="text-red-700 text-center">{error}</p>
          <button
            onClick={loadWalletData}
            className="mt-4 w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Back Button */}
        <div className="mb-6">
          <button
            onClick={() => navigate('/lobby')}
            className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 hover:text-gray-900 transition-colors shadow-sm"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </button>
        </div>

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">💎 My Wallet</h1>
          <p className="text-gray-600">Manage your gems and cash out your earnings</p>
        </div>

        {/* Balance Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {/* Current Balance */}
          <div className="bg-gradient-to-br from-purple-600 to-purple-700 rounded-xl p-6 text-white shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <Gem className="w-8 h-8" />
              <span className="text-sm opacity-80">Current Balance</span>
            </div>
            <div className="text-4xl font-bold mb-2">{walletData?.gem_balance?.toLocaleString()}</div>
            <div className="text-sm opacity-90">gems</div>
            <div className="mt-3 pt-3 border-t border-purple-500">
              <div className="flex items-center text-sm">
                <DollarSign className="w-4 h-4 mr-1" />
                {walletData?.usd_equivalent?.toFixed(2)} USD
              </div>
            </div>
          </div>

          {/* Total Earned */}
          <div className="bg-white rounded-xl p-6 shadow-lg border-2 border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <TrendingUp className="w-8 h-8 text-green-600" />
              <span className="text-sm text-gray-600">Total Earned</span>
            </div>
            <div className="text-4xl font-bold text-gray-900 mb-2">{walletData?.total_gems_earned?.toLocaleString()}</div>
            <div className="text-sm text-gray-600">gems</div>
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="flex items-center text-sm text-gray-700">
                <DollarSign className="w-4 h-4 mr-1" />
                {(walletData?.total_gems_earned / 1000).toFixed(2)} USD
              </div>
            </div>
          </div>

          {/* Total Cashed Out */}
          <div className="bg-white rounded-xl p-6 shadow-lg border-2 border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <History className="w-8 h-8 text-blue-600" />
              <span className="text-sm text-gray-600">Cashed Out</span>
            </div>
            <div className="text-4xl font-bold text-gray-900 mb-2">{walletData?.total_gems_cashed_out?.toLocaleString()}</div>
            <div className="text-sm text-gray-600">gems</div>
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="flex items-center text-sm text-gray-700">
                <DollarSign className="w-4 h-4 mr-1" />
                {(walletData?.total_gems_cashed_out / 1000).toFixed(2)} USD
              </div>
            </div>
          </div>
        </div>

        {/* Cash Out Section */}
        <div className="bg-white rounded-xl p-6 shadow-lg mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">💰 Cash Out</h2>
          
          {!walletData?.has_worker_id ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
              <div className="flex items-start">
                <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5 mr-3 flex-shrink-0" />
                <div>
                  <p className="text-yellow-800 font-semibold mb-1">MTurk Worker ID Required</p>
                  <p className="text-yellow-700 text-sm mb-2">
                    To cash out your gems, you need to add your MTurk Worker ID in your profile settings.
                  </p>
                  <a
                    href="/profile"
                    className="inline-flex items-center text-sm font-semibold text-yellow-800 hover:text-yellow-900 underline"
                  >
                    Go to Profile Settings →
                  </a>
                </div>
              </div>
            </div>
          ) : (
            <>
              <p className="text-gray-600 mb-4">
                Convert your gems to real money via MTurk. Minimum cashout: $2.00 (2,000 gems)
              </p>
              <button
                onClick={() => setShowCashoutModal(true)}
                disabled={walletData?.gem_balance < 2000}
                className={`px-6 py-3 rounded-lg font-bold text-white transition shadow-lg ${
                  walletData?.gem_balance >= 2000
                    ? 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700'
                    : 'bg-gray-300 cursor-not-allowed'
                }`}
              >
                Request Cash Out
              </button>
              {walletData?.gem_balance < 2000 && (
                <p className="text-sm text-gray-500 mt-2">
                  You need {(2000 - walletData.gem_balance).toLocaleString()} more gems to cash out
                </p>
              )}
            </>
          )}
        </div>

        {/* Transaction History */}
        <div className="bg-white rounded-xl p-6 shadow-lg">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">📜 Transaction History</h2>
          
          {transactions.length === 0 ? (
            <div className="text-center py-12">
              <History className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-600">No cashout transactions yet</p>
              <p className="text-sm text-gray-500 mt-2">Your cashout history will appear here</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">Date</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">Amount</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">Status</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">Completed</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((tx) => (
                    <tr key={tx.transaction_id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {formatDate(tx.created_at)}
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-sm">
                          <div className="font-semibold text-gray-900">${tx.amount_usd}</div>
                          <div className="text-gray-500">{tx.amount_gems.toLocaleString()} gems</div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {getStatusBadge(tx.status)}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {tx.completed_at ? formatDate(tx.completed_at) : '-'}
                      </td>
                      <td className="py-3 px-4">
                        {tx.status === 'pending' && (
                          <button
                            onClick={() => handleCancelTransaction(tx.transaction_id, tx.amount_gems)}
                            disabled={cancellingTx === tx.transaction_id}
                            className={`inline-flex items-center px-3 py-1 rounded-lg text-sm font-medium transition ${
                              cancellingTx === tx.transaction_id
                                ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                                : 'bg-red-50 text-red-700 hover:bg-red-100 border border-red-200'
                            }`}
                            title="Cancel this pending transaction and return gems to wallet"
                          >
                            {cancellingTx === tx.transaction_id ? (
                              <>
                                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-gray-500 mr-2"></div>
                                Cancelling...
                              </>
                            ) : (
                              <>
                                <X className="w-4 h-4 mr-1" />
                                Cancel
                              </>
                            )}
                          </button>
                        )}
                        {tx.status !== 'pending' && (
                          <span className="text-sm text-gray-400">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Info Box */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="font-bold text-blue-900 mb-2">How It Works</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• Earn gems by playing games (1000 gems = $1.00)</li>
            <li>• Cash out when you reach $2.00 minimum</li>
            <li>• We create a special MTurk HIT only you can see</li>
            <li>• Accept and complete the HIT to receive your payment</li>
            <li>• Payment processed within 1 hour of completion</li>
          </ul>
        </div>
      </div>

      {/* Cashout Modal */}
      {showCashoutModal && (
        <CashoutModal
          walletData={walletData}
          onClose={() => setShowCashoutModal(false)}
          onSuccess={() => {
            setShowCashoutModal(false);
            loadWalletData();
          }}
        />
      )}
    </div>
  );
};

export default Wallet;

