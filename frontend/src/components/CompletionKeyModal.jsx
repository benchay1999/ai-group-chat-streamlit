/**
 * Completion Key Modal
 * Displays after game ends with completion key for MTurk submission
 */

import React, { useState } from 'react';
import { Copy, Check, Trophy, ExternalLink } from 'lucide-react';
import toast from 'react-hot-toast';

const CompletionKeyModal = ({ completionKey, onClose, sessionId }) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(completionKey);
    setCopied(true);
    toast.success('Completion key copied to clipboard!');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full p-8 relative animate-fadeIn">
        {/* Success Icon */}
        <div className="flex justify-center mb-6">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center animate-bounce">
            <Trophy className="w-10 h-10 text-green-600" />
          </div>
        </div>

        {/* Title */}
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-2">
          Game Complete!
        </h2>
        <p className="text-center text-gray-600 mb-8">
          Thank you for participating. Here's your completion key for compensation.
        </p>

        {/* Completion Key Box */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 mb-6 border-2 border-blue-200">
          <label className="block text-sm font-semibold text-gray-700 mb-3">
            Your Completion Key:
          </label>
          <div className="bg-white rounded-lg p-4 mb-4 border border-gray-200">
            <p className="font-mono text-sm text-gray-800 break-all">
              {completionKey}
            </p>
          </div>
          <button
            onClick={copyToClipboard}
            className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 flex items-center justify-center gap-2 transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-5 h-5" />
                Copied to Clipboard!
              </>
            ) : (
              <>
                <Copy className="w-5 h-5" />
                Copy Completion Key
              </>
            )}
          </button>
        </div>

        {/* Instructions */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <h3 className="font-semibold text-gray-900 mb-2">Important Instructions:</h3>
          <ul className="text-sm text-gray-700 space-y-1">
            <li>• Copy this completion key and save it somewhere safe</li>
            <li>• Use this key to claim your payment on Mechanical Turk</li>
            <li>• This key is unique to your session and cannot be reused</li>
            <li>• If you're logged in, this key is automatically saved to your account</li>
          </ul>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3">
          {sessionId && (
            <a
              href={`/sessions/${sessionId}`}
              className="flex-1 bg-gray-100 text-gray-900 py-3 px-4 rounded-lg font-medium hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 flex items-center justify-center gap-2 transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              View Details
            </a>
          )}
          <button
            onClick={onClose}
            className="flex-1 bg-green-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default CompletionKeyModal;

