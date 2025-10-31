/**
 * CashoutModal Component
 * Modal for initiating a cashout transaction
 */

import React, { useState } from 'react';
import { X, DollarSign, ExternalLink, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import { requestCashout, checkHitReady, getCashoutStatus } from '../services/walletAPI';
import toast from 'react-hot-toast';

const CashoutModal = ({ walletData, onClose, onSuccess }) => {
  const [amountUsd, setAmountUsd] = useState('2.00');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [cashoutResult, setCashoutResult] = useState(null);
  const [hitReady, setHitReady] = useState(false);
  const [checkingHit, setCheckingHit] = useState(false);
  const [hitStatusMessage, setHitStatusMessage] = useState('Preparing MTurk HIT...');

  const maxAmount = (walletData.gem_balance / 1000).toFixed(2);
  const gemsNeeded = Math.ceil(parseFloat(amountUsd || 0) * 1000);

  const handleCashout = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const amount = parseFloat(amountUsd);
      
      // Validation
      if (isNaN(amount) || amount < 2.00) {
        setError('Minimum cashout amount is $2.00');
        setLoading(false);
        return;
      }
      
      if (amount > parseFloat(maxAmount)) {
        setError('Insufficient gems for this amount');
        setLoading(false);
        return;
      }
      
      const result = await requestCashout(amount);
      
      // Validate response has required fields
      if (!result.redemption_code) {
        setError('Failed to generate redemption code. Please try again.');
        return;
      }
      
      // Validate MTurk HIT URL
      if (!result.hit_url) {
        setError('MTurk HIT URL not provided. Please contact support.');
        return;
      }
      
      // Ensure it's a valid MTurk URL (not localhost)
      if (result.hit_url.includes('localhost') || result.hit_url.includes('127.0.0.1')) {
        setError('Invalid redemption URL. MTurk HIT URL required.');
        return;
      }
      
      setCashoutResult(result);
      setCheckingHit(true);
      setHitReady(false);
      
    } catch (err) {
      console.error('Cashout error:', err);
      const errorMsg = err.response?.data?.detail || 'Failed to create cashout';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // Poll HIT readiness
  React.useEffect(() => {
    if (!cashoutResult || hitReady) return;

    let pollInterval;
    let attempts = 0;
    const maxAttempts = 20; // Poll for up to 20 seconds

    const pollHitStatus = async () => {
      attempts++;
      
      try {
        const status = await checkHitReady(cashoutResult.transaction_id);
        
        if (status.ready) {
          setHitReady(true);
          setCheckingHit(false);
          setHitStatusMessage('✅ HIT is ready!');
          clearInterval(pollInterval);
          toast.success('MTurk HIT is ready! You can now access it.');
        } else {
          setHitStatusMessage(status.message || 'Checking...');
          
          if (attempts >= maxAttempts) {
            // After 20 seconds, stop polling and let user try anyway
            setHitReady(true);
            setCheckingHit(false);
            setHitStatusMessage('⚠️ Taking longer than expected. You can try accessing the HIT now.');
            clearInterval(pollInterval);
          }
        }
      } catch (err) {
        console.error('Error checking HIT status:', err);
        setHitStatusMessage('Checking HIT status...');
        
        if (attempts >= maxAttempts) {
          setHitReady(true);
          setCheckingHit(false);
          clearInterval(pollInterval);
        }
      }
    };

    // Start polling immediately, then every second
    pollHitStatus();
    pollInterval = setInterval(pollHitStatus, 1000);

    return () => clearInterval(pollInterval);
  }, [cashoutResult, hitReady]);

  // Poll transaction status to detect completion and auto-close
  React.useEffect(() => {
    if (!cashoutResult) return;

    let statusInterval;

    const checkTransactionStatus = async () => {
      try {
        const status = await getCashoutStatus(cashoutResult.transaction_id);
        
        // Check if transaction is completed
        if (status.status === 'COMPLETED') {
          toast.success('💰 Cashout completed! Payment has been processed.');
          clearInterval(statusInterval);
          
          // Auto-close modal after 2 seconds
          setTimeout(() => {
            onSuccess(); // This will refresh wallet data and close modal
          }, 2000);
        } else if (status.status === 'FAILED' || status.status === 'CANCELLED') {
          toast.error('Cashout was cancelled or failed. Please try again.');
          clearInterval(statusInterval);
          
          // Auto-close after 2 seconds
          setTimeout(() => {
            onSuccess();
          }, 2000);
        }
      } catch (err) {
        console.error('Error checking transaction status:', err);
      }
    };

    // Check every 5 seconds
    statusInterval = setInterval(checkTransactionStatus, 5000);

    return () => clearInterval(statusInterval);
  }, [cashoutResult, onSuccess]);

  if (cashoutResult) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <div className="bg-white rounded-xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
          {/* Success Header */}
          <div className="flex items-center gap-3 mb-6">
            <div className="bg-green-500 rounded-full p-3">
              <CheckCircle className="w-8 h-8 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-green-800">
                Redemption Code Generated! 🎉
              </h2>
              <p className="text-green-600">
                Use this code to claim your payout
              </p>
            </div>
          </div>

          {/* Amount Info */}
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-gray-900 mb-1">
                ${cashoutResult.amount_usd}
              </div>
              <div className="text-sm text-gray-600">
                ({cashoutResult.amount_gems.toLocaleString()} gems)
              </div>
            </div>
          </div>

          {/* Redemption Code */}
          <div className="bg-purple-50 border-2 border-purple-300 rounded-lg p-4 mb-6">
            <label className="block text-sm font-semibold text-purple-800 mb-2 text-center">
              Your Redemption Code:
            </label>
            <div className="bg-white rounded-lg p-4 mb-3">
              <code className="block text-center font-mono text-lg break-all text-purple-900">
                {cashoutResult.redemption_code}
              </code>
            </div>
            <button
              onClick={() => {
                navigator.clipboard.writeText(cashoutResult.redemption_code);
                toast.success('Code copied to clipboard!');
              }}
              className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              Copy Code
            </button>
          </div>

          {/* Instructions */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <h3 className="font-bold text-blue-900 mb-3">📋 How to Redeem:</h3>
            <ol className="text-sm text-blue-800 space-y-2 ml-6 list-decimal">
              <li>{cashoutResult.instructions.step1}</li>
              <li>{cashoutResult.instructions.step2}</li>
              <li>{cashoutResult.instructions.step3}</li>
              <li>{cashoutResult.instructions.step4}</li>
            </ol>
            <div className="mt-3 p-3 bg-blue-100 rounded text-sm text-blue-900">
              <strong>Note:</strong> {cashoutResult.instructions.note}
            </div>
          </div>

          {/* Redemption Buttons */}
          <div className="space-y-3 mb-4">
            {/* MTurk HIT Button (Primary) - Disabled while checking */}
            {!hitReady ? (
              <div className="block w-full py-4 bg-gray-400 text-white rounded-lg font-bold text-lg cursor-not-allowed flex items-center justify-center gap-3 relative">
                <div className="absolute inset-0 flex items-center justify-center bg-blue-600 bg-opacity-20 rounded-lg">
                  <div className="text-center px-4">
                    <Loader className="w-8 h-8 mx-auto mb-2 animate-spin" />
                    <div className="text-sm">{hitStatusMessage}</div>
                  </div>
                </div>
                <ExternalLink className="w-6 h-6 opacity-30" />
                <span className="opacity-30">Go to MTurk HIT</span>
              </div>
            ) : (
              <a
                href={cashoutResult.hit_url}
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full py-4 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-lg font-bold text-lg hover:from-green-600 hover:to-emerald-700 transition-all shadow-lg hover:shadow-xl flex items-center justify-center gap-3 animate-pulse"
              >
                <ExternalLink className="w-6 h-6" />
                Go to MTurk HIT ✨
              </a>
            )}

            {/* Dev/Test Mode Button (Sandbox only) */}
            {cashoutResult.dev_test_url && (
              <>
                <div className="text-center text-sm text-gray-500 py-2">
                  — OR (for testing only) —
                </div>
                <a
                  href={cashoutResult.dev_test_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full py-3 bg-yellow-500 text-white rounded-lg font-semibold hover:bg-yellow-600 transition-all flex items-center justify-center gap-2 border-2 border-yellow-600"
                >
                  🧪 Test Mode (Skip MTurk)
                </a>
                <div className="bg-yellow-50 border border-yellow-200 rounded p-2 text-xs text-yellow-800">
                  <strong>Test Mode:</strong> Use this to test redemption without MTurk API. For development/testing only.
                </div>
              </>
            )}
          </div>

          {/* Secondary Info */}
          <div className="text-xs text-gray-600 space-y-1 mb-4">
            <div>Transaction ID: {cashoutResult.transaction_id}</div>
            <div>Expires: {new Date(cashoutResult.expires_at).toLocaleString()}</div>
          </div>

          {/* Auto-close notification */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4 text-sm text-blue-800">
            <div className="flex items-center gap-2">
              <Loader className="w-4 h-4 animate-spin" />
              <span>Monitoring transaction status... This panel will auto-close when cashout is completed.</span>
            </div>
          </div>

          {/* Close Button */}
          <button
            onClick={onSuccess}
            className="w-full px-4 py-3 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition font-semibold"
          >
            Got It, Thanks!
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl max-w-md w-full p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">💰 Cash Out</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition"
          >
            <X className="w-6 h-6 text-gray-600" />
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Available Balance */}
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-4">
          <div className="text-sm text-purple-700 mb-1">Available Balance</div>
          <div className="text-2xl font-bold text-purple-900">
            {walletData.gem_balance.toLocaleString()} gems
          </div>
          <div className="text-sm text-purple-600">
            (${walletData.usd_equivalent.toFixed(2)} USD)
          </div>
        </div>

        {/* Amount Input */}
        <div className="mb-4">
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Amount to Cash Out (USD)
          </label>
          <div className="relative">
            <div className="absolute left-3 top-1/2 transform -translate-y-1/2">
              <DollarSign className="w-5 h-5 text-gray-400" />
            </div>
            <input
              type="number"
              min="2.00"
              max={maxAmount}
              step="0.01"
              value={amountUsd}
              onChange={(e) => setAmountUsd(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none text-lg font-semibold"
              placeholder="2.00"
            />
          </div>
          <div className="mt-2 flex justify-between text-sm text-gray-600">
            <span>Min: $2.00</span>
            <span>Max: ${maxAmount}</span>
          </div>
        </div>

        {/* Gems Calculation */}
        <div className="bg-gray-50 rounded-lg p-3 mb-4">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Gems Required:</span>
            <span className="font-bold text-gray-900">{gemsNeeded.toLocaleString()}</span>
          </div>
          <div className="flex justify-between items-center mt-1">
            <span className="text-sm text-gray-600">Remaining After:</span>
            <span className="font-bold text-gray-900">
              {Math.max(0, walletData.gem_balance - gemsNeeded).toLocaleString()}
            </span>
          </div>
        </div>

        {/* Quick Amount Buttons */}
        <div className="grid grid-cols-3 gap-2 mb-4">
          {['2.00', '5.00', maxAmount].map((amount) => (
            <button
              key={amount}
              onClick={() => setAmountUsd(amount)}
              className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-semibold text-gray-700 transition"
            >
              ${amount}
            </button>
          ))}
        </div>

        {/* Confirm Button */}
        <button
          onClick={handleCashout}
          disabled={loading || parseFloat(amountUsd) < 2 || parseFloat(amountUsd) > parseFloat(maxAmount)}
          className={`w-full py-3 rounded-lg font-bold text-white transition ${
            loading || parseFloat(amountUsd) < 2 || parseFloat(amountUsd) > parseFloat(maxAmount)
              ? 'bg-gray-300 cursor-not-allowed'
              : 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 shadow-lg'
          }`}
        >
          {loading ? 'Processing...' : 'Confirm Cash Out'}
        </button>

        {/* Info */}
        <p className="text-xs text-gray-500 mt-3 text-center">
          1000 gems = $1.00 USD • Minimum cashout: $2.00
        </p>
      </div>
    </div>
  );
};

export default CashoutModal;

