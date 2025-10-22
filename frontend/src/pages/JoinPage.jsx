/**
 * JoinPage
 * Join selected room
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { roomAPI } from '../services/api';
import { useGame } from '../context/GameContext';
import toast from 'react-hot-toast';

const JoinPage = () => {
  const navigate = useNavigate();
  const { selectedRoom, joinRoom } = useGame();
  const [joining, setJoining] = useState(false);

  if (!selectedRoom) {
    // Redirect to lobby if no room selected
    navigate('/');
    return null;
  }

  const handleJoin = async () => {
    setJoining(true);
    try {
      const result = await roomAPI.joinRoom(selectedRoom.room_code, {});

      if (result.success) {
        const playerId = result.player_id;
        joinRoom(selectedRoom.room_code, playerId);
        toast.success(`Joined as ${playerId}`);

        // Navigate based on room status
        if (result.can_start) {
          navigate('/game');
        } else {
          navigate('/waiting');
        }
      } else {
        toast.error(result.error || 'Failed to join room');
        navigate('/');
      }
    } catch (error) {
      console.error('Error joining room:', error);
      toast.error('Failed to join room');
      navigate('/');
    } finally {
      setJoining(false);
    }
  };

  const handleBack = () => {
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-blue-600 to-indigo-700 flex items-center justify-center p-6">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8 animate-fade-in">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Join Room</h1>
          <p className="text-gray-600">Ready to play?</p>
        </div>

        {/* Room Info */}
        <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl p-6 mb-8 border border-purple-200">
          <h2 className="text-xl font-bold text-gray-800 mb-4">
            {selectedRoom.room_name}
          </h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Room Code:</span>
              <span className="font-mono font-bold text-purple-600">
                {selectedRoom.room_code}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Players:</span>
              <span className="font-semibold text-gray-800">
                {selectedRoom.current_humans || 0} / {selectedRoom.max_humans}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Total Players:</span>
              <span className="font-semibold text-gray-800">
                {selectedRoom.total_players}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">AI Players:</span>
              <span className="font-semibold text-purple-600">
                {selectedRoom.total_players - selectedRoom.max_humans}
              </span>
            </div>
          </div>
        </div>

        {/* Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-blue-800">
            <strong>Note:</strong> You'll be assigned a random player number when you join.
            The game will start automatically when the room is full!
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={handleBack}
            className="flex-1 bg-gray-200 text-gray-700 py-3 px-6 rounded-lg font-semibold hover:bg-gray-300 transition-colors"
            disabled={joining}
          >
            Back
          </button>
          <button
            onClick={handleJoin}
            className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105"
            disabled={joining}
          >
            {joining ? 'Joining...' : 'Join Game'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default JoinPage;

