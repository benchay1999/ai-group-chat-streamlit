/**
 * MTurkAutoLogin Component
 * Automatically detects MTurk URL parameters and registers/logs in workers
 */

import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Loader2, AlertCircle, CheckCircle, Eye } from 'lucide-react';

const MTurkAutoLogin = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { mturkLogin, isAuthenticated } = useAuth();
  const [status, setStatus] = useState('detecting'); // detecting, authenticating, success, preview, error
  const [message, setMessage] = useState('');

  useEffect(() => {
    const handleMTurkAuth = async () => {
      // Check for MTurk parameters
      const workerId = searchParams.get('workerId');
      const assignmentId = searchParams.get('assignmentId');
      const hitId = searchParams.get('hitId');

      // No MTurk parameters - not an MTurk worker
      if (!workerId || !assignmentId || !hitId) {
        setStatus(null); // Hide component
        return;
      }

      // Already authenticated - skip
      if (isAuthenticated) {
        setStatus('success');
        setTimeout(() => setStatus(null), 2000);
        return;
      }

      // Check for preview mode
      if (assignmentId === 'ASSIGNMENT_ID_NOT_AVAILABLE') {
        setStatus('preview');
        setMessage('You are previewing this HIT. Please accept the HIT to participate.');
        return;
      }

      // Authenticate MTurk worker
      setStatus('authenticating');
      setMessage('Authenticating MTurk worker...');

      const result = await mturkLogin(workerId, assignmentId, hitId);

      if (result.success) {
        setStatus('success');
        setMessage('Authentication successful! Redirecting...');
        
        // Wait a moment then hide
        setTimeout(() => {
          setStatus(null);
        }, 2000);
      } else if (result.preview_mode) {
        setStatus('preview');
        setMessage(result.message || 'Preview mode - accept HIT to participate');
      } else {
        setStatus('error');
        setMessage(result.error || 'Authentication failed. Please try again.');
      }
    };

    handleMTurkAuth();
  }, [searchParams, mturkLogin, isAuthenticated]);

  // Don't render if no status
  if (!status) return null;

  return (
    <div className="fixed top-4 right-4 z-50 max-w-md animate-in slide-in-from-top-5 duration-300">
      {/* Detecting */}
      {status === 'detecting' && (
        <div className="bg-blue-500 text-white px-6 py-4 rounded-lg shadow-2xl flex items-center gap-3">
          <Loader2 className="w-5 h-5 animate-spin" />
          <div>
            <p className="font-semibold">Detecting MTurk parameters...</p>
          </div>
        </div>
      )}

      {/* Authenticating */}
      {status === 'authenticating' && (
        <div className="bg-gradient-to-r from-purple-500 to-indigo-500 text-white px-6 py-4 rounded-lg shadow-2xl">
          <div className="flex items-center gap-3 mb-2">
            <Loader2 className="w-5 h-5 animate-spin" />
            <p className="font-bold text-lg">MTurk Authentication</p>
          </div>
          <p className="text-sm opacity-90">{message}</p>
          <div className="mt-3 bg-white bg-opacity-20 rounded-full h-2 overflow-hidden">
            <div className="bg-white h-full w-2/3 animate-pulse"></div>
          </div>
        </div>
      )}

      {/* Success */}
      {status === 'success' && (
        <div className="bg-gradient-to-r from-green-500 to-emerald-500 text-white px-6 py-4 rounded-lg shadow-2xl">
          <div className="flex items-center gap-3">
            <div className="bg-white bg-opacity-20 rounded-full p-2">
              <CheckCircle className="w-6 h-6" />
            </div>
            <div>
              <p className="font-bold text-lg">Welcome, MTurk Worker! 🎯</p>
              <p className="text-sm opacity-90">{message}</p>
            </div>
          </div>
        </div>
      )}

      {/* Preview Mode */}
      {status === 'preview' && (
        <div className="bg-gradient-to-r from-yellow-500 to-orange-500 text-white px-6 py-4 rounded-lg shadow-2xl">
          <div className="flex items-start gap-3">
            <div className="bg-white bg-opacity-20 rounded-full p-2 flex-shrink-0">
              <Eye className="w-6 h-6" />
            </div>
            <div>
              <p className="font-bold text-lg mb-1">Preview Mode</p>
              <p className="text-sm opacity-90 leading-relaxed">{message}</p>
              <div className="mt-3 bg-white bg-opacity-20 rounded-lg px-3 py-2">
                <p className="text-xs font-semibold">💡 To participate:</p>
                <ol className="text-xs mt-1 space-y-1 opacity-90">
                  <li>1. Return to MTurk</li>
                  <li>2. Click "Accept HIT"</li>
                  <li>3. Come back to this page</li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {status === 'error' && (
        <div className="bg-gradient-to-r from-red-500 to-pink-500 text-white px-6 py-4 rounded-lg shadow-2xl">
          <div className="flex items-start gap-3">
            <div className="bg-white bg-opacity-20 rounded-full p-2 flex-shrink-0">
              <AlertCircle className="w-6 h-6" />
            </div>
            <div>
              <p className="font-bold text-lg mb-1">Authentication Error</p>
              <p className="text-sm opacity-90">{message}</p>
              <button
                onClick={() => window.location.reload()}
                className="mt-3 bg-white text-red-600 px-4 py-2 rounded-lg text-sm font-semibold hover:bg-opacity-90 transition-all"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MTurkAutoLogin;

