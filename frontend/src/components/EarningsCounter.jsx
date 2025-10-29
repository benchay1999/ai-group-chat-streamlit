/**
 * EarningsCounter Component
 * Animated counter that counts up from 0 to target value with glowing effect
 */

import { useState, useEffect } from 'react';

const EarningsCounter = ({ 
  target, 
  duration = 2000, 
  decimals = 2,
  prefix = '$',
  className = '',
  glowColor = 'green'
}) => {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let startTime;
    let animationFrame;

    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);

      // Easing function (ease-out cubic)
      const easeOut = 1 - Math.pow(1 - progress, 3);
      
      setCount(target * easeOut);

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      } else {
        setCount(target);
      }
    };

    animationFrame = requestAnimationFrame(animate);

    return () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
    };
  }, [target, duration]);

  const glowColors = {
    green: 'text-green-400',
    yellow: 'text-yellow-400',
    blue: 'text-blue-400',
    purple: 'text-purple-400',
    cyan: 'text-cyan-400',
  };

  return (
    <span className={`${glowColors[glowColor] || glowColors.green} ${className}`}>
      {prefix}{count.toFixed(decimals)}
    </span>
  );
};

export default EarningsCounter;

