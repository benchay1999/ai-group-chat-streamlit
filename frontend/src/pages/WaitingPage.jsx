/**
 * WaitingPage
 * Wait for players to join before game starts
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGame } from '../contexts/GameContext';
import { useRoomPolling } from '../hooks/useRoomPolling';
import { roomAPI } from '../services/api';
import toast from 'react-hot-toast';

const WaitingPage = () => {
  const navigate = useNavigate();
  const { roomCode, playerId, leaveRoom, saveActiveSession, clearActiveSession } = useGame();
  const { roomInfo, loading, error } = useRoomPolling(roomCode, 2000, !!roomCode);
  const [stakeInfo, setStakeInfo] = useState(null);

  // Save active session when component mounts (user is waiting in room)
  useEffect(() => {
    if (roomCode && playerId) {
      saveActiveSession(roomCode, playerId, 'waiting');
    }
  }, [roomCode, playerId, saveActiveSession]);

  // Fetch stake info for multi-human rooms
  useEffect(() => {
    const fetchStakeInfo = async () => {
      if (!roomCode || !roomInfo) return;
      
      // Only fetch for multi-human rooms
      if (roomInfo.max_humans > 1) {
        try {
          const response = await fetch(`${import.meta.env.VITE_API_URL}/api/rooms/${roomCode}/stake_info`, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
          });
          const data = await response.json();
          setStakeInfo(data);
        } catch (error) {
          console.debug('Error fetching stake info:', error);
        }
      }
    };
    
    fetchStakeInfo();
    
    // Poll every 3 seconds
    const interval = setInterval(fetchStakeInfo, 3000);
    return () => clearInterval(interval);
  }, [roomCode, roomInfo]);

  // Redirect if no room code
  useEffect(() => {
    if (!roomCode) {
      navigate('/');
    }
  }, [roomCode, navigate]);

  // Auto-navigate when game starts (update session status to in_progress)
  useEffect(() => {
    if (roomInfo && roomInfo.room_status === 'in_progress') {
      toast.success('Game starting!');
      // Update session status to in_progress
      if (roomCode && playerId) {
        saveActiveSession(roomCode, playerId, 'in_progress');
      }
      navigate('/game');
    }
  }, [roomInfo, navigate, roomCode, playerId, saveActiveSession]);

  // Check if room no longer exists
  useEffect(() => {
    if (error || (roomInfo && !roomInfo.exists)) {
      toast.error('Room no longer exists');
      // Clear active session when room no longer exists
      clearActiveSession();
      leaveRoom();
      navigate('/');
    }
  }, [error, roomInfo, leaveRoom, navigate, clearActiveSession]);

  const handleLeave = async () => {
    try {
      await roomAPI.leaveRoom(roomCode, playerId);
      // Clear active session when explicitly leaving
      clearActiveSession();
      leaveRoom();
      toast.success('Left room');
      navigate('/');
    } catch (error) {
      console.error('Error leaving room:', error);
      clearActiveSession();
      leaveRoom();
      navigate('/');
    }
  };

  if (!roomInfo || loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-600 via-blue-600 to-indigo-700 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-16 w-16 border-b-2 border-white mb-4"></div>
          <p className="text-white text-xl">Loading...</p>
        </div>
      </div>
    );
  }

  const currentHumans = roomInfo.current_humans?.length || 0;
  const maxHumans = roomInfo.max_humans || 1;
  const progress = (currentHumans / maxHumans) * 100;

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-blue-600 to-indigo-700 flex items-center justify-center p-6">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full p-8 animate-fade-in">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">Waiting for Players</h1>
          <p className="text-gray-600">Game will start automatically when room is full</p>
        </div>

        {/* Player Counter */}
        <div className="bg-gradient-to-r from-purple-100 to-blue-100 rounded-xl p-8 mb-6 text-center">
          <div className="text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-blue-600 mb-2">
            {currentHumans} / {maxHumans}
          </div>
          <p className="text-gray-700 font-semibold">Players Joined</p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
            <div
              className="bg-gradient-to-r from-purple-500 to-blue-500 h-4 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <p className="text-center text-sm text-gray-600 mt-2">
            {maxHumans - currentHumans} more player{maxHumans - currentHumans !== 1 ? 's' : ''} needed
          </p>
        </div>

        {/* Room Info */}
        <div className="bg-gray-50 rounded-xl p-6 mb-6">
          <h3 className="font-semibold text-gray-700 mb-4">Room Details</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Room Code:</span>
              <p className="font-mono font-bold text-purple-600 text-lg">
                {roomInfo.room_code}
              </p>
            </div>
            <div>
              <span className="text-gray-600">Your ID:</span>
              <p className="font-bold text-blue-600">{playerId}</p>
            </div>
            <div>
              <span className="text-gray-600">Total Players:</span>
              <p className="font-semibold text-gray-800">{roomInfo.total_players}</p>
            </div>
            <div>
              <span className="text-gray-600">AI Players:</span>
              <p className="font-semibold text-purple-600">
                {roomInfo.total_players - maxHumans}
              </p>
            </div>
            
            {/* Stake Information for Multi-Human Rooms */}
            {roomInfo.max_humans > 1 && stakeInfo && (
              <>
                <div className="col-span-2 border-t border-gray-300 pt-3 mt-3">
                  <span className="text-gray-600 block mb-2 font-semibold">💎 Stake Information</span>
                </div>
                <div>
                  <span className="text-gray-600">Stake %:</span>
                  <p className={`font-semibold ${
                    stakeInfo.stake_percentage === 0 ? 'text-gray-600' :
                    stakeInfo.stake_percentage <= 10 ? 'text-green-600' :
                    stakeInfo.stake_percentage <= 30 ? 'text-yellow-600' :
                    stakeInfo.stake_percentage <= 50 ? 'text-orange-600' :
                    'text-red-600'
                  }`}>
                    {stakeInfo.stake_percentage}%
                  </p>
                </div>
                <div>
                  <span className="text-gray-600">Min Stake:</span>
                  <p className="font-bold text-indigo-600">
                    {stakeInfo.minimum_stake > 0 ? `${stakeInfo.minimum_stake} gems` : 'Calculating...'}
                  </p>
                </div>
                {stakeInfo.stake_percentage > 0 && (
                  <div className="col-span-2 bg-yellow-50 border border-yellow-200 rounded p-3 text-sm">
                    <p className="text-yellow-800">
                      <strong>⚠️ Stakes Active:</strong> Each player risks the minimum stake. 
                      Win by getting the most votes AND identifying all other humans correctly!
                    </p>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Players Joined Indicator (Anonymous to prevent spoilers) */}
        {roomInfo.current_humans && roomInfo.current_humans.length > 0 && (
          <div className="bg-gray-50 rounded-xl p-6 mb-6">
            <h3 className="font-semibold text-gray-700 mb-3">Players Ready</h3>
            <div className="flex items-center justify-center gap-2 py-4">
              {[...Array(roomInfo.current_humans.length)].map((_, idx) => (
                <div
                  key={idx}
                  className="w-12 h-12 bg-gradient-to-br from-purple-400 to-blue-400 rounded-full flex items-center justify-center shadow-lg animate-fade-in"
                  style={{ animationDelay: `${idx * 0.1}s` }}
                >
                  <span className="text-xl">👤</span>
                </div>
              ))}
            </div>
            <p className="text-center text-sm text-gray-600 mt-4">
              {roomInfo.current_humans.length} {roomInfo.current_humans.length === 1 ? 'player has' : 'players have'} joined
            </p>
          </div>
        )}

        {/* Share Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-blue-800">
            <strong>Share this code:</strong> {roomInfo.room_code}
            <br />
            Other players can join by selecting this room from the lobby.
          </p>
        </div>

        {/* Leave Button */}
        <button
          onClick={handleLeave}
          className="w-full bg-red-500 text-white py-3 px-6 rounded-lg font-semibold hover:bg-red-600 transition-colors"
        >
          Leave Room
        </button>

        {/* Animation */}
        <div className="mt-6 text-center">
          <div className="flex justify-center gap-2">
            <span className="w-3 h-3 bg-purple-500 rounded-full animate-bounce"></span>
            <span className="w-3 h-3 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></span>
            <span className="w-3 h-3 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WaitingPage;

