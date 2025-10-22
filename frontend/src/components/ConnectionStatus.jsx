/**
 * ConnectionStatus Component
 * Shows WebSocket connection status indicator
 */

const ConnectionStatus = ({ status }) => {
  const statusConfig = {
    connected: {
      color: 'bg-green-500',
      text: 'Connected',
      icon: '●',
    },
    connecting: {
      color: 'bg-yellow-500',
      text: 'Connecting...',
      icon: '◐',
    },
    disconnected: {
      color: 'bg-red-500',
      text: 'Disconnected',
      icon: '○',
    },
    error: {
      color: 'bg-red-500',
      text: 'Error',
      icon: '✕',
    },
  };

  const config = statusConfig[status] || statusConfig.disconnected;

  return (
    <div className="flex items-center gap-2 px-3 py-1 bg-white rounded-full shadow-md border border-gray-200">
      <span className={`${config.color} w-2 h-2 rounded-full animate-pulse`}></span>
      <span className="text-xs font-semibold text-gray-700">{config.text}</span>
    </div>
  );
};

export default ConnectionStatus;

