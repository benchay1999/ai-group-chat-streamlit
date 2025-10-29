import React from 'react';

const StatsCard = ({ title, value, subtitle, icon, color = 'purple' }) => {
  const colorClasses = {
    purple: 'border-purple-500 bg-purple-900/20',
    blue: 'border-blue-500 bg-blue-900/20',
    green: 'border-green-500 bg-green-900/20',
    yellow: 'border-yellow-500 bg-yellow-900/20',
    red: 'border-red-500 bg-red-900/20'
  };

  return (
    <div className={`${colorClasses[color]} border-l-4 rounded-lg p-6 backdrop-blur-sm`}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-gray-400 text-sm font-medium mb-2">{title}</p>
          <p className="text-3xl font-bold text-white">{value}</p>
          {subtitle && (
            <p className="text-gray-500 text-sm mt-2">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className="text-4xl ml-4 opacity-60">{icon}</div>
        )}
      </div>
    </div>
  );
};

export default StatsCard;

