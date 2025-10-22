/**
 * PhaseTimer Component
 * Countdown timer with color coding based on urgency
 */

import { useEffect, useState } from 'react';

const PhaseTimer = ({ initialTime, phase }) => {
  const [timeLeft, setTimeLeft] = useState(initialTime);

  useEffect(() => {
    setTimeLeft(initialTime);
  }, [initialTime, phase]);

  useEffect(() => {
    if (timeLeft <= 0) return;

    const interval = setInterval(() => {
      setTimeLeft((prev) => Math.max(0, prev - 1));
    }, 1000);

    return () => clearInterval(interval);
  }, [timeLeft]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getColorClass = () => {
    const percentage = timeLeft / initialTime;
    if (percentage > 0.5) return 'text-white';
    if (percentage > 0.2) return 'text-yellow-300';
    return 'text-red-300';
  };

  return (
    <div className="flex items-center gap-2 bg-black bg-opacity-20 rounded-lg px-3 py-2">
      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <span className={`text-2xl font-bold font-mono ${getColorClass()} drop-shadow-lg`}>
        {formatTime(timeLeft)}
      </span>
    </div>
  );
};

export default PhaseTimer;

