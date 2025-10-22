/**
 * RoomCard Component
 * Displays a room in the lobby with join button
 */

const RoomCard = ({ room, onJoin }) => {
  const { room_code, room_name, current_humans, max_humans, total_players } = room;

  return (
    <div className="bg-white rounded-lg shadow-lg hover:shadow-xl transition-shadow duration-300 p-6 border border-gray-200">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-xl font-bold text-gray-800">{room_name}</h3>
          <p className="text-sm text-gray-500 font-mono mt-1">Code: {room_code}</p>
        </div>
        <span className="px-3 py-1 bg-green-100 text-green-700 text-xs font-semibold rounded-full">
          Waiting
        </span>
      </div>

      <div className="space-y-2 mb-4">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Players:</span>
          <span className="font-semibold text-gray-800">
            {current_humans} / {max_humans}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Total Players:</span>
          <span className="font-semibold text-gray-800">{total_players}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">AI Players:</span>
          <span className="font-semibold text-purple-600">{total_players - max_humans}</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
        <div
          className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${(current_humans / max_humans) * 100}%` }}
        ></div>
      </div>

      <button
        onClick={() => onJoin(room)}
        className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-2 px-4 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 transition-all duration-200 transform hover:scale-105"
      >
        Join Room
      </button>
    </div>
  );
};

export default RoomCard;

