/**
 * CreateRoomModal Component
 * Modal for creating a new room with configuration
 */

import { useState } from 'react';

const CreateRoomModal = ({ isOpen, onClose, onCreate }) => {
  const [maxHumans, setMaxHumans] = useState(1);
  const [totalPlayers, setTotalPlayers] = useState(5);
  const [creating, setCreating] = useState(false);

  if (!isOpen) return null;

  const aiCount = totalPlayers - maxHumans;

  const handleCreate = async () => {
    setCreating(true);
    try {
      await onCreate({ max_humans: maxHumans, total_players: totalPlayers });
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 animate-fade-in">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-800">Create New Room</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
            disabled={creating}
          >
            ×
          </button>
        </div>

        <div className="space-y-6">
          {/* Max Humans Slider */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Maximum Human Players: {maxHumans}
            </label>
            <input
              type="range"
              min="1"
              max="4"
              value={maxHumans}
              onChange={(e) => {
                const newMax = parseInt(e.target.value);
                setMaxHumans(newMax);
                // Ensure total players is at least max humans
                if (totalPlayers < newMax) {
                  setTotalPlayers(newMax);
                }
              }}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
              disabled={creating}
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>1</span>
              <span>2</span>
              <span>3</span>
              <span>4</span>
            </div>
          </div>

          {/* Total Players Slider */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Total Players: {totalPlayers}
            </label>
            <input
              type="range"
              min={maxHumans}
              max="12"
              value={totalPlayers}
              onChange={(e) => setTotalPlayers(parseInt(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              disabled={creating}
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>{maxHumans}</span>
              <span>12</span>
            </div>
          </div>

          {/* Preview */}
          <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-4 border border-purple-200">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Room Preview</h3>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Human Players:</span>
                <span className="font-semibold text-gray-800">{maxHumans}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">AI Players:</span>
                <span className="font-semibold text-purple-600">{aiCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Total:</span>
                <span className="font-semibold text-blue-600">{totalPlayers}</span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 bg-gray-200 text-gray-700 py-2 px-4 rounded-lg font-semibold hover:bg-gray-300 transition-colors"
              disabled={creating}
            >
              Cancel
            </button>
            <button
              onClick={handleCreate}
              className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 text-white py-2 px-4 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={creating}
            >
              {creating ? 'Creating...' : 'Create Room'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CreateRoomModal;

