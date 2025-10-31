/**
 * CashoutConfirm Page
 * MTurk HIT page where workers submit their redemption code
 */

import React, { useState, useEffect } from 'react';
import { CheckCircle, AlertCircle, Loader, Copy } from 'lucide-react';
import api from '../services/api';

const CashoutConfirm = () => {
  const [redemptionCode, setRedemptionCode] = useState('');
  const [workerId, setWorkerId] = useState('');
  const [assignmentId, setAssignmentId] = useState('');
  const [hitId, setHitId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [isPreview, setIsPreview] = useState(true);

  useEffect(() => {
    // Get MTurk parameters from URL
    const params = new URLSearchParams(window.location.search);
    const wid = params.get('workerId');
    const aid = params.get('assignmentId');
    const hid = params.get('hitId');
    
    // DEV MODE: Check if we're in development (no real MTurk params)
    const isDevMode = params.get('dev') === 'true' || window.location.hostname === 'localhost';
    
    if (isDevMode && !aid) {
      // Use fake dev IDs for testing
      setWorkerId(wid || 'DEV_WORKER_TEST');
      setAssignmentId('DEV_ASSIGNMENT_TEST');
      setHitId(hid || 'DEV_HIT_TEST');
      setIsPreview(false); // Allow submission in dev mode
      console.log('🧪 DEV MODE: Using test MTurk IDs');
    } else {
      setWorkerId(wid || '');
      setAssignmentId(aid || '');
      setHitId(hid || '');
      
      // Check if this is preview mode
      setIsPreview(aid === 'ASSIGNMENT_ID_NOT_AVAILABLE' || !aid);
    }
  }, []);

  const handleSubmit = async () => {
    if (!redemptionCode.trim()) {
      setError('Please enter your redemption code');
      return;
    }
    
    if (isPreview) {
      setError('Please accept the HIT first before submitting');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.post('/api/wallet/redeem', {
        redemption_code: redemptionCode,
        worker_id: workerId,
        assignment_id: assignmentId,
        hit_id: hitId
      });
      
      setSuccess(response.data);
      
      // Auto-submit to MTurk after 3 seconds (skip in dev mode)
      const isDevMode = assignmentId.startsWith('DEV_') || window.location.hostname === 'localhost';
      if (!isDevMode) {
        setTimeout(() => {
          submitToMTurk();
        }, 3000);
      } else {
        console.log('🧪 DEV MODE: Skipping MTurk submission');
      }
      
    } catch (err) {
      console.error('Redemption error:', err);
      setError(err.response?.data?.detail || 'Failed to redeem code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const submitToMTurk = () => {
    // Determine environment
    const environment = localStorage.getItem('mturk_environment') || 'sandbox';
    const submitUrl = environment === 'production' 
      ? 'https://www.mturk.com/mturk/externalSubmit'
      : 'https://workersandbox.mturk.com/mturk/externalSubmit';

    // Create form and submit
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = submitUrl;

    const assignmentField = document.createElement('input');
    assignmentField.type = 'hidden';
    assignmentField.name = 'assignmentId';
    assignmentField.value = assignmentId;
    form.appendChild(assignmentField);

    const codeField = document.createElement('input');
    codeField.type = 'hidden';
    codeField.name = 'redemption_code';
    codeField.value = redemptionCode;
    form.appendChild(codeField);

    document.body.appendChild(form);
    form.submit();
  };

  if (success) {
    const isDevMode = assignmentId.startsWith('DEV_') || window.location.hostname === 'localhost';
    
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-50 p-4 flex items-center justify-center">
        <div className="bg-white rounded-xl p-8 max-w-md w-full shadow-lg">
          <div className="flex flex-col items-center text-center">
            <div className="bg-green-500 rounded-full p-4 mb-4">
              <CheckCircle className="w-16 h-16 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-green-800 mb-3">
              {isDevMode ? 'Redemption Successful! 🧪' : 'Payment Approved! 🎉'}
            </h1>
            <p className="text-lg text-green-700 mb-4">
              ${success.amount_usd} {isDevMode ? 'redeemed (dev mode)' : 'has been approved'}
            </p>
            {!isDevMode && (
              <p className="text-sm text-gray-600 mb-6">
                Submitting HIT to MTurk... You can close this page once redirected.
              </p>
            )}
            {isDevMode && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4 w-full">
                <p className="text-sm text-yellow-800 font-semibold">
                  🧪 Development Mode
                </p>
                <p className="text-xs text-yellow-700 mt-1">
                  No actual MTurk payment processed. This is for testing only.
                </p>
              </div>
            )}
            <div className="bg-green-50 rounded-lg p-4 w-full">
              <p className="text-sm text-green-800">
                {success.message}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (isPreview) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 p-4 flex items-center justify-center">
        <div className="bg-white rounded-xl p-8 max-w-md w-full shadow-lg">
          <div className="flex flex-col items-center text-center">
            <div className="bg-blue-500 rounded-full p-4 mb-4">
              <AlertCircle className="w-16 h-16 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-blue-900 mb-3">
              ChatGame Cashout HIT
            </h1>
            <p className="text-blue-700 mb-6">
              Please accept this HIT to submit your redemption code and claim your payout.
            </p>
            <div className="bg-blue-50 rounded-lg p-4 w-full text-left">
              <h3 className="font-bold text-blue-900 mb-2">How it works:</h3>
              <ol className="text-sm text-blue-800 space-y-2 ml-4 list-decimal">
                <li>Play games on ChatGame to earn gems</li>
                <li>Request a cashout and get a redemption code</li>
                <li>Accept this HIT and paste your code</li>
                <li>Get paid instantly!</li>
              </ol>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 p-4">
      <div className="max-w-2xl mx-auto pt-12">
        {/* Header */}
        <div className="bg-white rounded-xl p-6 shadow-lg mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            💎 ChatGame Cashout
          </h1>
          <p className="text-gray-600">
            Enter your redemption code to claim your payout
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-semibold text-red-800">Error</p>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        )}

        {/* Redemption Form */}
        <div className="bg-white rounded-xl p-6 shadow-lg mb-6">
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Redemption Code
          </label>
          <p className="text-sm text-gray-600 mb-3">
            Paste the redemption code you received from ChatGame
          </p>
          <textarea
            value={redemptionCode}
            onChange={(e) => setRedemptionCode(e.target.value)}
            placeholder="Enter your 64-character redemption code here..."
            rows={3}
            className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none font-mono text-sm resize-none"
          />
          
          <button
            onClick={handleSubmit}
            disabled={loading || !redemptionCode.trim()}
            className={`mt-4 w-full py-4 rounded-lg font-bold text-white transition shadow-lg ${
              loading || !redemptionCode.trim()
                ? 'bg-gray-300 cursor-not-allowed'
                : 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700'
            }`}
          >
            {loading ? (
              <div className="flex items-center justify-center gap-2">
                <Loader className="w-5 h-5 animate-spin" />
                Processing...
              </div>
            ) : (
              'Submit & Claim Payment'
            )}
          </button>
        </div>

        {/* Info Box */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="font-bold text-blue-900 mb-3">ℹ️ Information</h3>
          <ul className="text-sm text-blue-800 space-y-2">
            <li>• Your code is unique and can only be used once</li>
            <li>• Payment is processed immediately upon submission</li>
            <li>• Codes expire after 7 days</li>
            <li>• Don't share your code with anyone</li>
            <li>• If you encounter issues, contact the requester</li>
          </ul>
        </div>

        {/* Debug Info */}
        {workerId && (
          <div className="mt-6 bg-gray-50 rounded-lg p-4 text-xs text-gray-600">
            <details>
              <summary className="cursor-pointer font-semibold">Debug Info</summary>
              <div className="mt-2 space-y-1 font-mono">
                <div>Worker ID: {workerId}</div>
                <div>Assignment ID: {assignmentId?.substring(0, 30)}...</div>
                <div>HIT ID: {hitId?.substring(0, 30)}...</div>
              </div>
            </details>
          </div>
        )}
      </div>
    </div>
  );
};

export default CashoutConfirm;
