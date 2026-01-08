/**
 * ActiveSessionGuard
 * Detects active game sessions and forces user to rejoin
 * Prevents navigation to other pages until session is rejoined or cleared
 */

import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useGame } from '../contexts/GameContext';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import toast from 'react-hot-toast';

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

const ActiveSessionGuard = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { getActiveSession, clearActiveSession, joinRoom, roomCode, playerId } = useGame();
  const { isAuthenticated } = useAuth();
  
  const [showRejoinModal, setShowRejoinModal] = useState(false);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [verifying, setVerifying] = useState(true);
  const [rejoining, setRejoining] = useState(false);

  // Check for active session on mount and location change
  useEffect(() => {
    const checkActiveSession = async () => {
      const localSession = getActiveSession();
      
      if (!localSession) {
        setVerifying(false);
        return;
      }

      console.log('🔍 Found local session:', localSession);

      let validatedSession = null;

      // Verify session is still valid on backend (for authenticated users)
      if (isAuthenticated) {
        try {
          const token = localStorage.getItem('access_token');
          const response = await axios.get(`${API_BASE_URL}/api/users/active-session`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {}
          });

          if (response.data.has_active_session) {
            console.log('✅ Backend confirmed active session:', response.data);
            validatedSession = response.data;
          } else {
            // Backend says no active session - clear local storage
            console.log('❌ Backend says no active session, clearing local storage');
            clearActiveSession();
          }
        } catch (error) {
          console.error('Error verifying session:', error);
          // On error, assume local session is valid
          validatedSession = localSession;
        }
      } else {
        // For anonymous users, trust local storage
        validatedSession = localSession;
      }

      if (validatedSession) {
        setSessionInfo(validatedSession);
        
        // Handle property name differences between backend (snake_case) and local storage (camelCase)
        const targetRoomCode = validatedSession.roomCode || validatedSession.room_code;
        const targetPlayerId = validatedSession.playerId || validatedSession.player_id;
        const status = validatedSession.roomStatus || validatedSession.room_status;
        
        // Check if we should automatically restore instead of showing modal
        // This happens when user refreshes the page while in game/waiting
        const isGamePage = location.pathname === '/game';
        const isWaitingPage = location.pathname === '/waiting';
        
        // Determine if session status matches current page
        // Status can be 'waiting' or 'in_progress' (which covers discussion, voting etc)
        const matchesGame = isGamePage && (status === 'in_progress' || status === 'discussion' || status === 'voting');
        const matchesWaiting = isWaitingPage && status === 'waiting';

        if (matchesGame || matchesWaiting) {
          // If we are on the correct page for the session state, just restore context
          // Only update if not already set to avoid infinite loops
          if (roomCode !== targetRoomCode || playerId !== targetPlayerId) {
             console.log('🔄 Automatically restoring session context');
             joinRoom(targetRoomCode, targetPlayerId);
          }
          setShowRejoinModal(false);
        } else {
          // We are on a different page (e.g. lobby), so show the modal
          setShowRejoinModal(true);
        }
      }

      setVerifying(false);
    };

    checkActiveSession();
  }, [location.pathname, isAuthenticated, getActiveSession, clearActiveSession, joinRoom, roomCode, playerId]);

  const handleRejoin = async () => {
    setRejoining(true);
    
    try {
      const { roomCode, playerId } = sessionInfo;
      
      console.log('🔄 Rejoining session:', { roomCode, playerId });
      
      // Update game context
      joinRoom(roomCode, playerId);
      
      // Navigate to appropriate page based on status
      if (sessionInfo.roomStatus === 'waiting' || sessionInfo.room_status === 'waiting') {
        navigate('/waiting');
      } else {
        navigate('/game');
      }
      
      setShowRejoinModal(false);
      toast.success('Rejoined your game!');
    } catch (error) {
      console.error('Error rejoining:', error);
      toast.error('Failed to rejoin game');
      setRejoining(false);
    }
  };

  const handleClearSession = () => {
    clearActiveSession();
    setShowRejoinModal(false);
    setSessionInfo(null);
    toast.success('Session cleared');
  };

  // Show loading spinner while verifying
  if (verifying) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-purple-500 mx-auto mb-4"></div>
          <p className="text-white text-lg">Checking for active session...</p>
        </div>
      </div>
    );
  }

  // Show rejoin modal if active session exists
  if (showRejoinModal && sessionInfo) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50">
        <div className="bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 rounded-2xl shadow-2xl max-w-md w-full mx-4 p-8 border-4 border-purple-500 animate-pulse-slow">
          <div className="text-center mb-6">
            <div className="text-6xl mb-4">🎮</div>
            <h2 className="text-3xl font-bold text-white mb-2">
              Active Game Found!
            </h2>
            <p className="text-purple-200 text-lg">
              You have an active game session
            </p>
          </div>

          <div className="bg-black bg-opacity-30 rounded-lg p-4 mb-6 border border-purple-400">
            <div className="flex justify-between items-center text-white mb-2">
              <span className="text-purple-300">Room:</span>
              <span className="font-bold text-xl">{sessionInfo.roomCode || sessionInfo.room_code}</span>
            </div>
            <div className="flex justify-between items-center text-white mb-2">
              <span className="text-purple-300">Player:</span>
              <span className="font-bold">{sessionInfo.playerId || sessionInfo.player_id}</span>
            </div>
            <div className="flex justify-between items-center text-white">
              <span className="text-purple-300">Status:</span>
              <span className="font-bold capitalize">{sessionInfo.roomStatus || sessionInfo.room_status}</span>
            </div>
          </div>

          <div className="space-y-3">
            <button
              onClick={handleRejoin}
              disabled={rejoining}
              className="w-full bg-gradient-to-r from-green-500 to-emerald-600 text-white font-bold py-4 px-6 rounded-lg hover:from-green-600 hover:to-emerald-700 transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg text-lg"
            >
              {rejoining ? (
                <span className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Rejoining...
                </span>
              ) : (
                '🎯 Rejoin Game'
              )}
            </button>

            <button
              onClick={handleClearSession}
              disabled={rejoining}
              className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-6 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
            >
              ❌ Leave Game & Clear Session
            </button>
          </div>

          <p className="text-purple-300 text-sm mt-6 text-center">
            You must rejoin or leave your active game to continue
          </p>
        </div>
      </div>
    );
  }

  // No active session or on game page - render children normally
  return <>{children}</>;
};

export default ActiveSessionGuard;

