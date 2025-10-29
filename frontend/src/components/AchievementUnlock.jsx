import React, { useEffect, useState } from 'react';
import { Trophy, X } from 'lucide-react';

const AchievementUnlock = ({ achievements, onClose }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (!achievements || achievements.length === 0) {
      onClose();
      return;
    }

    // Auto-advance to next achievement after 4 seconds
    const timer = setTimeout(() => {
      if (currentIndex < achievements.length - 1) {
        setCurrentIndex(currentIndex + 1);
      } else {
        // All achievements shown, start closing
        setVisible(false);
        setTimeout(onClose, 300);
      }
    }, 4000);

    return () => clearTimeout(timer);
  }, [currentIndex, achievements, onClose]);

  if (!achievements || achievements.length === 0 || !visible) {
    return null;
  }

  const achievement = achievements[currentIndex];

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50 bg-black bg-opacity-50 backdrop-blur-sm animate-fadeIn">
      <div className="bg-gradient-to-br from-yellow-600 to-yellow-800 rounded-lg p-8 max-w-md w-full mx-4 shadow-2xl transform animate-bounceIn">
        <div className="flex justify-between items-start mb-4">
          <Trophy className="text-yellow-200" size={32} />
          <button
            onClick={() => {
              setVisible(false);
              setTimeout(onClose, 300);
            }}
            className="text-yellow-200 hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>
        
        <div className="text-center">
          <h2 className="text-3xl font-bold text-white mb-2">Achievement Unlocked!</h2>
          
          <div className="text-6xl my-6 animate-bounce">{achievement.icon}</div>
          
          <h3 className="text-2xl font-bold text-white mb-2">{achievement.name}</h3>
          <p className="text-yellow-100 mb-4">{achievement.description}</p>
          
          <div className="bg-yellow-900/50 rounded-lg p-3 inline-block">
            <p className="text-yellow-200 font-bold">+{achievement.points} Points</p>
          </div>

          {achievements.length > 1 && (
            <div className="mt-4 flex justify-center gap-2">
              {achievements.map((_, index) => (
                <div
                  key={index}
                  className={`h-2 w-2 rounded-full transition-colors ${
                    index === currentIndex ? 'bg-white' : 'bg-yellow-900/50'
                  }`}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AchievementUnlock;

