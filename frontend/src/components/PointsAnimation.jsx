import React, { useEffect, useState } from 'react';

const PointsAnimation = ({ points, breakdown, onComplete }) => {
  const [visible, setVisible] = useState(true);
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    // Trigger animation
    setTimeout(() => setAnimated(true), 100);

    // Auto-close after 3 seconds
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(onComplete, 300);
    }, 3000);

    return () => clearTimeout(timer);
  }, [onComplete]);

  if (!visible) return null;

  return (
    <div className={`transition-all duration-300 ${animated ? 'opacity-100 transform translate-y-0' : 'opacity-0 transform -translate-y-4'}`}>
      <div className="bg-gradient-to-r from-green-600 to-emerald-600 rounded-lg p-6 shadow-lg">
        <div className="text-center mb-4">
          <h3 className="text-2xl font-bold text-white mb-1">Points Earned!</h3>
          <p className="text-4xl font-extrabold text-yellow-300">+{points}</p>
        </div>
        
        {breakdown && Object.keys(breakdown).length > 0 && (
          <div className="space-y-2">
            <p className="text-sm text-green-100 font-semibold mb-2">Breakdown:</p>
            {Object.entries(breakdown).map(([key, value]) => (
              <div key={key} className="flex justify-between items-center text-sm">
                <span className="text-green-50 capitalize">
                  {key.replace(/_/g, ' ')}
                </span>
                <span className="text-yellow-200 font-bold">+{value}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PointsAnimation;

