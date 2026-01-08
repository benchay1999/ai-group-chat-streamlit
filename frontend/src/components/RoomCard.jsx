/**
 * RoomCard Component
 * Displays a room in the lobby with join button
 */

import { useLanguage } from '../contexts/LanguageContext';
import { Languages } from 'lucide-react';

const RoomCard = ({ room, onJoin, userGemBalance }) => {
  const { t } = useLanguage();
  const { 
    room_code, 
    room_name, 
    current_humans, 
    max_humans, 
    total_players, 
    language,
    stake_percentage = 0,
    minimum_stake = 0,
    has_stakes = false
  } = room;
  
  // Check if user has enough gems to join
  const hasEnoughGems = max_humans > 1 ? (userGemBalance >= 250) : true;
  const canJoin = hasEnoughGems;

  return (
    <div className="bg-white rounded-lg shadow-lg hover:shadow-xl transition-shadow duration-300 p-6 border border-gray-200">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-xl font-bold text-gray-800">{room_name}</h3>
          <p className="text-sm text-gray-500 font-mono mt-1">{t('room.code')}: {room_code}</p>
        </div>
        <div className="flex flex-col gap-1 items-end">
          <span className="px-3 py-1 bg-green-100 text-green-700 text-xs font-semibold rounded-full">
            {t('room.waiting')}
          </span>
          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-semibold rounded-full flex items-center gap-1">
            <Languages className="w-3 h-3" />
            {language === 'korean' ? t('room.korean') : t('room.english')}
          </span>
        </div>
      </div>

      <div className="space-y-2 mb-4">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">{t('room.players')}:</span>
          <span className="font-semibold text-gray-800">
            {current_humans} / {max_humans}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">{t('room.totalPlayers')}:</span>
          <span className="font-semibold text-gray-800">{total_players}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">{t('room.aiPlayers')}:</span>
          <span className="font-semibold text-purple-600">{total_players - max_humans}</span>
        </div>
        
        {/* Stake Information for Multi-Human Rooms */}
        {max_humans > 1 && (
          <>
            <div className="flex justify-between text-sm border-t border-gray-200 pt-2 mt-2">
              <span className="text-gray-600">💎 Stakes:</span>
              <span className={`font-semibold ${
                stake_percentage === 0 ? 'text-gray-600' :
                stake_percentage <= 10 ? 'text-green-600' :
                stake_percentage <= 30 ? 'text-yellow-600' :
                stake_percentage <= 50 ? 'text-orange-600' :
                'text-red-600'
              }`}>
                {stake_percentage}%
                {stake_percentage === 0 && <span className="text-xs ml-1">(No Stakes)</span>}
              </span>
            </div>
            {has_stakes && minimum_stake > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Min Stake:</span>
                <span className="font-semibold text-indigo-600">{minimum_stake} gems</span>
              </div>
            )}
            <div className="flex justify-between text-xs text-gray-500 bg-yellow-50 p-2 rounded">
              <span>⚠️ Entry:</span>
              <span className="font-semibold">250+ gems required</span>
            </div>
          </>
        )}
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
        disabled={!canJoin}
        className={`w-full py-2 px-4 rounded-lg font-semibold transition-all duration-200 ${
          canJoin
            ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:from-purple-700 hover:to-blue-700 transform hover:scale-105'
            : 'bg-gray-300 text-gray-500 cursor-not-allowed'
        }`}
        title={!hasEnoughGems ? `Insufficient gems. Need 250+ gems (you have ${userGemBalance})` : ''}
      >
        {!hasEnoughGems ? `Need 250+ gems` : t('room.joinRoom')}
      </button>
    </div>
  );
};

export default RoomCard;

