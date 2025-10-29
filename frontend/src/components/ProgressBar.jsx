import React from 'react';

const ProgressBar = ({ current, max, label, color = 'purple', showPercentage = true }) => {
  const percentage = max > 0 ? Math.min((current / max) * 100, 100) : 0;
  
  const colorClasses = {
    purple: 'bg-purple-600',
    blue: 'bg-blue-600',
    green: 'bg-green-600',
    yellow: 'bg-yellow-600',
    red: 'bg-red-600'
  };

  return (
    <div className="w-full">
      {label && (
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-300">{label}</span>
          {showPercentage && (
            <span className="text-sm text-gray-400">{percentage.toFixed(1)}%</span>
          )}
        </div>
      )}
      <div className="w-full bg-gray-700 rounded-full h-3 overflow-hidden">
        <div
          className={`h-full ${colorClasses[color] || colorClasses.purple} transition-all duration-500 ease-out rounded-full`}
          style={{ width: `${percentage}%` }}
        >
          <div className="h-full w-full bg-gradient-to-r from-transparent to-white opacity-20"></div>
        </div>
      </div>
      {current !== undefined && max !== undefined && (
        <div className="flex justify-between items-center mt-1">
          <span className="text-xs text-gray-500">{current.toLocaleString()} / {max.toLocaleString()}</span>
        </div>
      )}
    </div>
  );
};

export default ProgressBar;

