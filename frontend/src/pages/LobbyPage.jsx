/**
 * LobbyPage
 * Browse and create rooms
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { roomAPI } from '../services/api';
import { useGame } from '../context/GameContext';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../contexts/AuthContext';
import RoomCard from '../components/RoomCard';
import CreateRoomModal from '../components/CreateRoomModal';
import toast from 'react-hot-toast';
import { User, LogIn } from 'lucide-react';

const LobbyPage = () => {
  const navigate = useNavigate();
  const { selectRoom, joinRoom } = useGame();
  const { t, toggleLanguage, language } = useLanguage();
  const { isAuthenticated, user } = useAuth();
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [serverOnline, setServerOnline] = useState(false);

  const loadRooms = async () => {
    try {
      setLoading(true);
      const data = await roomAPI.listRooms(page, 10);
      setRooms(data.rooms || []);
      setTotalPages(data.total_pages || 0);
      setServerOnline(true);
    } catch (error) {
      console.error('Error loading rooms:', error);
      toast.error(t('message.failedToLoadRooms'));
      setServerOnline(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Check server health
    roomAPI.healthCheck()
      .then(() => setServerOnline(true))
      .catch(() => setServerOnline(false));

    loadRooms();
  }, [page]);

  // Auto-refresh every 30 seconds (reduced to save bandwidth)
  useEffect(() => {
    const interval = setInterval(loadRooms, 30000);
    return () => clearInterval(interval);
  }, [page]);

  const handleJoinRoom = (room) => {
    selectRoom(room);
    navigate('/join');
  };

  const handleCreateRoom = async (config) => {
    try {
      const result = await roomAPI.createRoom(config);
      
      if (result.success) {
        toast.success(`${t('message.roomCreated')}: ${result.room_code}`);
        
        // Store room info
        selectRoom({
          room_code: result.room_code,
          room_name: result.room_name,
          max_humans: result.max_humans,
          total_players: result.total_players,
        });
        
        // Auto-join the room as creator
        try {
          const joinResult = await roomAPI.joinRoom(result.room_code, {});
          
          if (joinResult.success) {
            const playerId = joinResult.player_id;
            joinRoom(result.room_code, playerId);
            toast.success(`${t('message.joinedAs')} ${playerId}`);
            
            setIsCreateModalOpen(false);
            
            // Navigate based on room status
            if (joinResult.can_start) {
              navigate('/game');
            } else {
              navigate('/waiting');
            }
          } else {
            toast.error(t('message.failedToJoin'));
            setIsCreateModalOpen(false);
          }
        } catch (joinError) {
          console.error('Error joining created room:', joinError);
          toast.error(t('message.failedToJoin'));
          setIsCreateModalOpen(false);
        }
      } else {
        toast.error(result.error || t('message.failedToCreateRoom'));
      }
    } catch (error) {
      console.error('Error creating room:', error);
      toast.error(t('message.failedToCreateRoom'));
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-blue-600 to-indigo-700">
      {/* Header */}
      <div className="bg-white bg-opacity-10 backdrop-blur-md border-b border-white border-opacity-20">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2">{t('lobby.title')}</h1>
              <p className="text-blue-100">{t('lobby.subtitle')}</p>
            </div>
            <div className="flex items-center gap-4">
              {/* Auth Status */}
              {isAuthenticated ? (
                <button
                  onClick={() => navigate('/dashboard')}
                  className="flex items-center gap-2 px-4 py-2 bg-white bg-opacity-20 rounded-full hover:bg-opacity-30 transition-all"
                  title="Go to Dashboard"
                >
                  <User className="w-4 h-4 text-white" />
                  <span className="text-sm font-semibold text-white">
                    {user?.user_id}
                  </span>
                </button>
              ) : (
                <button
                  onClick={() => navigate('/login')}
                  className="flex items-center gap-2 px-4 py-2 bg-white bg-opacity-20 rounded-full hover:bg-opacity-30 transition-all"
                  title="Login"
                >
                  <LogIn className="w-4 h-4 text-white" />
                  <span className="text-sm font-semibold text-white">
                    Login
                  </span>
                </button>
              )}
              {/* Language Switcher */}
              <button
                onClick={toggleLanguage}
                className="flex items-center gap-2 px-4 py-2 bg-white bg-opacity-20 rounded-full hover:bg-opacity-30 transition-all"
                title="Toggle Language"
              >
                <span className="text-2xl">{language === 'korean' ? '🇰🇷' : '🇺🇸'}</span>
                <span className="text-sm font-semibold text-white">
                  {language === 'korean' ? 'KO' : 'EN'}
                </span>
              </button>
              {/* Server Status */}
              <div className="flex items-center gap-2 px-4 py-2 bg-white bg-opacity-20 rounded-full">
                <span className={`w-3 h-3 rounded-full ${serverOnline ? 'bg-green-400' : 'bg-red-400'} animate-pulse`}></span>
                <span className="text-sm font-semibold text-white">
                  {serverOnline ? t('lobby.serverOnline') : t('lobby.serverOffline')}
                </span>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(true)}
                className="bg-white text-purple-600 px-6 py-3 rounded-lg font-bold hover:bg-gray-100 transition-all transform hover:scale-105 shadow-lg"
              >
                + {t('lobby.createRoom')}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Game Description Banner */}
        <div className="mb-8 bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 rounded-2xl p-8 text-white shadow-2xl transform hover:scale-105 transition-all duration-300">
          <div className="flex items-start gap-6">
            <div className="flex-shrink-0">
              <div className="w-16 h-16 bg-white bg-opacity-20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                <span className="text-4xl">🎭</span>
              </div>
            </div>
            <div className="flex-1">
              <h2 className="text-3xl font-bold mb-3 drop-shadow-lg">{t('game.banner.title')}</h2>
              <p className="text-lg leading-relaxed opacity-95 mb-4">
                <strong>{t('game.banner.challenge')}</strong> {t('game.banner.description')}
              </p>
              <div className="flex flex-wrap gap-4">
                <div className="flex items-center gap-2 bg-white bg-opacity-20 rounded-full px-4 py-2 backdrop-blur-sm">
                  <span className="text-2xl">💬</span>
                  <span className="font-semibold">{t('game.banner.chat')}</span>
                </div>
                <div className="flex items-center gap-2 bg-white bg-opacity-20 rounded-full px-4 py-2 backdrop-blur-sm">
                  <span className="text-2xl">🤔</span>
                  <span className="font-semibold">{t('game.banner.analyze')}</span>
                </div>
                <div className="flex items-center gap-2 bg-white bg-opacity-20 rounded-full px-4 py-2 backdrop-blur-sm">
                  <span className="text-2xl">🗳️</span>
                  <span className="font-semibold">{t('game.banner.vote')}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white">
            {t('lobby.availableRooms')} ({rooms.length})
          </h2>
          <button
            onClick={loadRooms}
            disabled={loading}
            className="bg-white bg-opacity-20 text-white px-4 py-2 rounded-lg font-semibold hover:bg-opacity-30 transition-all disabled:opacity-50"
          >
            {loading ? t('lobby.refreshing') : '🔄 ' + t('lobby.refresh')}
          </button>
        </div>

        {/* Loading State */}
        {loading && rooms.length === 0 && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
            <p className="text-white mt-4">{t('lobby.loading')}</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && rooms.length === 0 && (
          <div className="text-center py-12 bg-white bg-opacity-10 rounded-xl backdrop-blur-md">
            <p className="text-white text-xl mb-4">{t('lobby.noRooms')}</p>
            <p className="text-blue-100 mb-6">{t('lobby.noRoomsSubtitle')}</p>
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="bg-white text-purple-600 px-6 py-3 rounded-lg font-bold hover:bg-gray-100 transition-all"
            >
              {t('lobby.createRoom')}
            </button>
          </div>
        )}

        {/* Room Grid */}
        {rooms.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {rooms.map((room) => (
              <RoomCard key={room.room_code} room={room} onJoin={handleJoinRoom} />
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex justify-center items-center gap-4 mt-8">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="bg-white bg-opacity-20 text-white px-4 py-2 rounded-lg font-semibold hover:bg-opacity-30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              ← {t('lobby.previous')}
            </button>
            <span className="text-white font-semibold">
              {t('lobby.page')} {page + 1} {t('lobby.of')} {totalPages}
            </span>
            <button
              onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
              disabled={page >= totalPages - 1}
              className="bg-white bg-opacity-20 text-white px-4 py-2 rounded-lg font-semibold hover:bg-opacity-30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t('lobby.next')} →
            </button>
          </div>
        )}
      </div>

      {/* Create Room Modal */}
      <CreateRoomModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreateRoom}
      />
    </div>
  );
};

export default LobbyPage;

