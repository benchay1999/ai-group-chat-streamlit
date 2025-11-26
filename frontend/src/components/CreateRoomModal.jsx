/**
 * CreateRoomModal Component
 * Modal for creating a new room with configuration
 */

import { useState } from 'react';
import { useLanguage } from '../context/LanguageContext';

const CreateRoomModal = ({ isOpen, onClose, onCreate }) => {
  const { t } = useLanguage();
  const [maxHumans, setMaxHumans] = useState(1);
  const [totalPlayers, setTotalPlayers] = useState(5);
  const [roomLanguage, setRoomLanguage] = useState('english');
  const [discussionDuration, setDiscussionDuration] = useState(180); // 3 minutes default
  const [votingDuration, setVotingDuration] = useState(60); // 1 minute default
  const [stakePercentage, setStakePercentage] = useState(10); // 10% default for multi-human
  const [creating, setCreating] = useState(false);

  if (!isOpen) return null;

  const aiCount = totalPlayers - maxHumans;
  
  // Calculate minimum total players based on game rules
  // Solo-human games (maxHumans = 1) MUST have at least 1 AI agent, so min total = 2
  // Multi-human games can have 0 AI agents, so min total = maxHumans
  const minTotalPlayers = maxHumans === 1 ? 2 : maxHumans;

  const handleCreate = async () => {
    // Validation: Solo-human games must have AI agents
    if (maxHumans === 1 && totalPlayers < 2) {
      alert('Solo-human games must have at least 1 AI agent. Please increase the total players to at least 2.');
      return;
    }
    
    setCreating(true);
    try {
      await onCreate({ 
        max_humans: maxHumans, 
        total_players: totalPlayers,
        language: roomLanguage,
        discussion_duration: discussionDuration,
        voting_duration: votingDuration,
        stake_percentage: maxHumans > 1 ? stakePercentage : 0  // Only for multi-human games
      });
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 animate-fade-in">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-800">{t('modal.title')}</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
            disabled={creating}
          >
            ×
          </button>
        </div>

        <div className="space-y-6">
          {/* Max Humans Slider */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              {t('modal.maxHumans')}: {maxHumans}
            </label>
            <input
              type="range"
              min="1"
              max="5"
              value={maxHumans}
              onChange={(e) => {
                const newMax = parseInt(e.target.value);
                setMaxHumans(newMax);
                // Calculate minimum total players based on game rules
                const newMinTotal = newMax === 1 ? 2 : newMax;
                // Ensure total players meets minimum requirement
                if (totalPlayers < newMinTotal) {
                  setTotalPlayers(newMinTotal);
                }
              }}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
              disabled={creating}
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>1</span>
              <span>2</span>
              <span>3</span>
              <span>4</span>
              <span>5</span>
            </div>
          </div>

          {/* Total Players Slider */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              {t('modal.totalPlayers')}: {totalPlayers}
            </label>
            <input
              type="range"
              min={minTotalPlayers}
              max="12"
              value={totalPlayers}
              onChange={(e) => setTotalPlayers(parseInt(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              disabled={creating}
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>{minTotalPlayers}</span>
              <span>12</span>
            </div>
            {maxHumans === 1 && aiCount === 0 && (
              <p className="text-xs text-red-500 mt-1">⚠️ Solo-human games require at least 1 AI agent</p>
            )}
          </div>

          {/* Language Selector */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              {t('modal.language')}
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => setRoomLanguage('english')}
                className={`flex-1 py-2 px-4 rounded-lg font-semibold transition-all ${
                  roomLanguage === 'english'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
                disabled={creating}
              >
                🇺🇸 {t('room.english')}
              </button>
              <button
                onClick={() => setRoomLanguage('korean')}
                className={`flex-1 py-2 px-4 rounded-lg font-semibold transition-all ${
                  roomLanguage === 'korean'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
                disabled={creating}
              >
                🇰🇷 {t('room.korean')}
              </button>
            </div>
          </div>

          {/* Discussion Duration */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              {t('modal.discussionDuration')}
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => setDiscussionDuration(60)}
                className={`flex-1 py-2 px-4 rounded-lg font-semibold transition-all text-xs ${
                  discussionDuration === 60
                    ? 'bg-yellow-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
                disabled={creating}
                title="Quick debug mode"
              >
                ⚡ 1m<br/><span className="text-[10px] opacity-80">(Debug)</span>
              </button>
              <button
                onClick={() => setDiscussionDuration(180)}
                className={`flex-1 py-2 px-4 rounded-lg font-semibold transition-all ${
                  discussionDuration === 180
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
                disabled={creating}
              >
                ⏱️ 3 {t('modal.minutes')}
              </button>
              <button
                onClick={() => setDiscussionDuration(240)}
                className={`flex-1 py-2 px-4 rounded-lg font-semibold transition-all ${
                  discussionDuration === 240
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
                disabled={creating}
              >
                ⏱️ 4 {t('modal.minutes')}
              </button>
            </div>
          </div>

          {/* Voting Duration */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              {t('modal.votingDuration')}
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => setVotingDuration(30)}
                className={`flex-1 py-2 px-4 rounded-lg font-semibold transition-all text-xs ${
                  votingDuration === 30
                    ? 'bg-yellow-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
                disabled={creating}
                title="Quick debug mode"
              >
                ⚡ 30s<br/><span className="text-[10px] opacity-80">(Debug)</span>
              </button>
              <button
                onClick={() => setVotingDuration(60)}
                className={`flex-1 py-2 px-4 rounded-lg font-semibold transition-all ${
                  votingDuration === 60
                    ? 'bg-orange-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
                disabled={creating}
              >
                🗳️ 1 {t('modal.minute')}
              </button>
              <button
                onClick={() => setVotingDuration(120)}
                className={`flex-1 py-2 px-4 rounded-lg font-semibold transition-all ${
                  votingDuration === 120
                    ? 'bg-orange-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
                disabled={creating}
              >
                🗳️ 2 {t('modal.minutes')}
              </button>
            </div>
          </div>

          {/* Stake Percentage (Multi-Human Only) */}
          {maxHumans > 1 && (
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                💎 Stake Percentage
              </label>
              <div className="flex gap-2">
                <button
                  onClick={() => setStakePercentage(0)}
                  className={`flex-1 py-2 px-2 rounded-lg font-semibold transition-all text-xs ${
                    stakePercentage === 0
                      ? 'bg-gray-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                  disabled={creating}
                >
                  0%<br/><span className="text-[10px] opacity-80">No Stakes</span>
                </button>
                <button
                  onClick={() => setStakePercentage(10)}
                  className={`flex-1 py-2 px-2 rounded-lg font-semibold transition-all text-xs ${
                    stakePercentage === 10
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                  disabled={creating}
                >
                  10%<br/><span className="text-[10px] opacity-80">Low</span>
                </button>
                <button
                  onClick={() => setStakePercentage(30)}
                  className={`flex-1 py-2 px-2 rounded-lg font-semibold transition-all text-xs ${
                    stakePercentage === 30
                      ? 'bg-yellow-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                  disabled={creating}
                >
                  30%<br/><span className="text-[10px] opacity-80">Med</span>
                </button>
                <button
                  onClick={() => setStakePercentage(50)}
                  className={`flex-1 py-2 px-2 rounded-lg font-semibold transition-all text-xs ${
                    stakePercentage === 50
                      ? 'bg-orange-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                  disabled={creating}
                >
                  50%<br/><span className="text-[10px] opacity-80">High</span>
                </button>
                <button
                  onClick={() => setStakePercentage(100)}
                  className={`flex-1 py-2 px-2 rounded-lg font-semibold transition-all text-xs ${
                    stakePercentage === 100
                      ? 'bg-red-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                  disabled={creating}
                >
                  100%<br/><span className="text-[10px] opacity-80">All-in</span>
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                💎 Minimum 250 gems required to join multi-human rooms
              </p>
            </div>
          )}

          {/* Preview */}
          <div className={`bg-gradient-to-r rounded-lg p-4 border ${
            maxHumans === 1 && aiCount === 0 
              ? 'from-red-50 to-orange-50 border-red-300' 
              : 'from-purple-50 to-blue-50 border-purple-200'
          }`}>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">{t('modal.preview')}</h3>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">{t('modal.humanPlayers')}:</span>
                <span className="font-semibold text-gray-800">{maxHumans}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">{t('modal.aiPlayers')}:</span>
                <span className={`font-semibold ${maxHumans === 1 && aiCount === 0 ? 'text-red-600' : 'text-purple-600'}`}>
                  {aiCount}
                  {maxHumans === 1 && aiCount === 0 && <span className="text-xs ml-1">⚠️</span>}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">{t('modal.total')}:</span>
                <span className="font-semibold text-blue-600">{totalPlayers}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">{t('modal.language')}:</span>
                <span className="font-semibold text-green-600">
                  {roomLanguage === 'korean' ? '🇰🇷 ' + t('room.korean') : '🇺🇸 ' + t('room.english')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">{t('modal.discussionDuration')}:</span>
                <span className={`font-semibold ${discussionDuration === 60 ? 'text-yellow-600' : 'text-green-600'}`}>
                  {discussionDuration === 60 ? '⚡' : '⏱️'} {discussionDuration / 60} {discussionDuration === 60 ? t('modal.minute') : t('modal.minutes')}
                  {discussionDuration === 60 && <span className="text-[10px] ml-1">(Debug)</span>}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">{t('modal.votingDuration')}:</span>
                <span className={`font-semibold ${votingDuration === 30 ? 'text-yellow-600' : 'text-orange-600'}`}>
                  {votingDuration === 30 ? '⚡' : '🗳️'} {votingDuration < 60 ? votingDuration + 's' : (votingDuration / 60) + (votingDuration === 60 ? ' ' + t('modal.minute') : ' ' + t('modal.minutes'))}
                  {votingDuration === 30 && <span className="text-[10px] ml-1">(Debug)</span>}
                </span>
              </div>
              {maxHumans > 1 && (
                <div className="flex justify-between">
                  <span className="text-gray-600">💎 Stakes:</span>
                  <span className={`font-semibold ${
                    stakePercentage === 0 ? 'text-gray-600' :
                    stakePercentage === 10 ? 'text-green-600' :
                    stakePercentage === 30 ? 'text-yellow-600' :
                    stakePercentage === 50 ? 'text-orange-600' :
                    'text-red-600'
                  }`}>
                    {stakePercentage}%
                    {stakePercentage === 0 && <span className="text-xs ml-1">(No Stakes)</span>}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 bg-gray-200 text-gray-700 py-2 px-4 rounded-lg font-semibold hover:bg-gray-300 transition-colors"
              disabled={creating}
            >
              {t('modal.cancel')}
            </button>
            <button
              onClick={handleCreate}
              className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 text-white py-2 px-4 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={creating || (maxHumans === 1 && aiCount === 0)}
              title={maxHumans === 1 && aiCount === 0 ? 'Solo-human games must have at least 1 AI agent' : ''}
            >
              {creating ? t('modal.creating') : t('modal.create')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CreateRoomModal;

