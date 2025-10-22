/**
 * ChatWindow Component
 * Enhanced chat display with typing indicators and animations
 */

import { useEffect, useRef } from 'react';

const ChatWindow = ({ chat, typing, currentPlayerId }) => {
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat, typing]);

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-gray-50 space-y-4">
      {chat.length === 0 && (
        <div className="text-center text-gray-400 mt-8">
          <p className="text-lg">No messages yet...</p>
          <p className="text-sm mt-2">Start the conversation!</p>
        </div>
      )}

      {chat.map((msg, idx) => {
        const isCurrentPlayer = msg.sender === currentPlayerId;
        return (
          <div
            key={idx}
            className={`flex ${isCurrentPlayer ? 'justify-end' : 'justify-start'} animate-fade-in`}
          >
            <div
              className={`max-w-md rounded-lg p-3 shadow-sm ${
                isCurrentPlayer
                  ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white'
                  : 'bg-white text-gray-800'
              }`}
            >
              <p className={`text-xs font-semibold mb-1 ${
                isCurrentPlayer ? 'text-blue-100' : 'text-gray-500'
              }`}>
                {msg.sender}
              </p>
              <p className="text-sm leading-relaxed">{msg.message}</p>
            </div>
          </div>
        );
      })}

      {/* Typing Indicators */}
      {typing.length > 0 && (
        <div className="flex justify-start animate-fade-in">
          <div className="bg-white rounded-lg p-3 shadow-sm">
            <p className="text-xs text-gray-500 mb-1">
              {typing.join(', ')} {typing.length > 1 ? 'are' : 'is'} typing
            </p>
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></span>
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
            </div>
          </div>
        </div>
      )}

      <div ref={chatEndRef} />
    </div>
  );
};

export default ChatWindow;
