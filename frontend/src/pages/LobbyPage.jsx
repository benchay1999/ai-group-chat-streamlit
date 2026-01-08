/**
 * LobbyPage
 * Browse and create rooms
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { roomAPI } from '../services/api';
import { useGame } from '../contexts/GameContext';
import { useLanguage } from '../contexts/LanguageContext';
import { useAuth } from '../contexts/AuthContext';
import { useHeartbeat } from '../hooks/useHeartbeat';
import walletAPI from '../services/walletAPI';
import RoomCard from '../components/RoomCard';
import CreateRoomModal from '../components/CreateRoomModal';
import MTurkAutoLogin from '../components/MTurkAutoLogin';
import toast from 'react-hot-toast';
import { User, LogIn, Award, Trophy, Mail, Copy, Check, Languages, Loader, AlertCircle, Bug } from 'lucide-react';

const LobbyPage = () => {
  const navigate = useNavigate();
  const { selectRoom, joinRoom, getActiveSession } = useGame();
  const { t, toggleLanguage, language } = useLanguage();
  const { isAuthenticated, user } = useAuth();
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [serverOnline, setServerOnline] = useState(false);
  const [onlineUsers, setOnlineUsers] = useState(0);
  const [adminRoomStats, setAdminRoomStats] = useState(null);
  const [showEmail, setShowEmail] = useState(false);
  const [emailCopied, setEmailCopied] = useState(false);
  const [gemBalance, setGemBalance] = useState(0);
  
  // New state for API retry/connecting status
  const [isReconnecting, setIsReconnecting] = useState(false);

  // Send heartbeat to track this user as online
  useHeartbeat();

  const handleCopyEmail = () => {
    const email = 'benchay@kaist.ac.kr';
    navigator.clipboard.writeText(email).then(() => {
      setEmailCopied(true);
      toast.success('Email copied to clipboard!');
      setTimeout(() => setEmailCopied(false), 2000);
    }).catch(err => {
      console.error('Failed to copy email:', err);
      toast.error('Failed to copy email');
    });
  };

  const loadRooms = async () => {
    try {
      // Don't show full loading spinner for background refresh
      // Only show if rooms list is empty
      if (rooms.length === 0) {
        setLoading(true);
      }
      
      const data = await roomAPI.listRooms(page, 10);
      setRooms(data.rooms || []);
      setTotalPages(data.total_pages || 0);
      setServerOnline(true);
      setIsReconnecting(false);
    } catch (error) {
      console.error('Error loading rooms:', error);
      
      // Check if it's a rate limit error (429) or connection error
      if (error.response?.status === 429) {
        setIsReconnecting(true);
        // Don't show toast for rate limits, just show connecting state
      } else {
        toast.error(t('message.failedToLoadRooms'));
        setServerOnline(false);
      }
    } finally {
      setLoading(false);
    }
  };

  const loadOnlineUsers = async () => {
    try {
      const data = await roomAPI.getOnlineUsers();
      setOnlineUsers(data.total_online || 0);
    } catch (error) {
      console.debug('Error loading online users:', error);
      // Silently fail - don't disrupt user experience
    }
  };

  const loadAdminRoomStats = async () => {
    // Only load for admin users
    if (user?.role !== 'admin') {
      return;
    }
    
    try {
      const data = await roomAPI.getAdminRoomStats();
      setAdminRoomStats(data);
    } catch (error) {
      console.debug('Error loading admin room stats:', error);
      // Silently fail - don't disrupt user experience
    }
  };

  const loadGemBalance = async () => {
    // Only load for authenticated users
    if (!isAuthenticated) {
      setGemBalance(0);
      return;
    }
    
    try {
      const data = await walletAPI.getWalletBalance();
      setGemBalance(data.gem_balance || 0);
    } catch (error) {
      console.debug('Error loading gem balance:', error);
      setGemBalance(0);
      // Silently fail - don't disrupt user experience
    }
  };

  useEffect(() => {
    // Check server health
    roomAPI.healthCheck()
      .then(() => setServerOnline(true))
      .catch(() => setServerOnline(false));

    loadRooms();
    loadOnlineUsers();
    loadAdminRoomStats();
    loadGemBalance();
  }, [page, user, isAuthenticated]);

  // Auto-refresh every 30 seconds (reduced to save bandwidth)
  useEffect(() => {
    const interval = setInterval(() => {
      loadRooms();
      loadOnlineUsers();
      loadAdminRoomStats();
      loadGemBalance();
    }, 30000);
    return () => clearInterval(interval);
  }, [page, user, isAuthenticated]);

  const handleJoinRoom = (room) => {
    selectRoom(room);
    navigate('/join');
  };

  const handleCreateRoom = async (config) => {
    // Client-side validation: Check for active session
    const activeSession = getActiveSession();
    if (activeSession) {
      toast.error('You already have an active game. Please leave it first.');
      console.log('❌ Blocked create attempt - active session exists:', activeSession);
      setIsCreateModalOpen(false);
      return;
    }

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
      {/* MTurk Auto-Login Component */}
      <MTurkAutoLogin />
      
      {/* Header */}
      <div className="bg-white bg-opacity-10 backdrop-blur-md border-b border-white border-opacity-20">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2">{t('lobby.title')}</h1>
              
              {/* Online Users Count */}
              <div className="flex items-center gap-2 mt-2">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-green-500 bg-opacity-20 rounded-full text-green-100 text-sm font-medium">
                  <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                  {onlineUsers} {onlineUsers === 1 ? 'user' : 'users'} online
                </span>
              </div>
            </div>
            <div className="flex items-center gap-4">
              {/* Leaderboard Button */}
              <button
                onClick={() => navigate('/leaderboard')}
                className="flex items-center gap-2 px-4 py-2 bg-yellow-400 bg-opacity-90 rounded-full hover:bg-opacity-100 transition-all transform hover:scale-105 shadow-lg"
                title="View Leaderboard"
              >
                <Trophy className="w-4 h-4 text-yellow-900" />
                <span className="text-sm font-semibold text-yellow-900">
                  {t('lobby.leaderboard')}
                </span>
              </button>
              {/* Auth Status */}
              {isAuthenticated ? (
                <button
                  onClick={() => navigate('/dashboard')}
                  className="flex items-center gap-2 px-4 py-2 bg-white bg-opacity-20 rounded-full hover:bg-opacity-30 transition-all group"
                  title="Go to Dashboard"
                >
                  {user?.is_mturk_worker ? (
                    <Award className="w-4 h-4 text-yellow-300 animate-pulse" />
                  ) : (
                    <User className="w-4 h-4 text-white" />
                  )}
                  <span className="text-sm font-semibold text-white">
                    {user?.user_id}
                  </span>
                  {user?.is_mturk_worker && (
                    <span className="text-xs bg-yellow-400 text-yellow-900 px-2 py-0.5 rounded-full font-bold">
                      MTurk
                    </span>
                  )}
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
                <Languages className="w-4 h-4 text-white" />
                <span className="text-sm font-semibold text-white">
                  {language === 'korean' ? 'KO' : 'EN'}
                </span>
              </button>
              {/* Server Status */}
              <div className="flex items-center gap-2 px-4 py-2 bg-white bg-opacity-20 rounded-full">
                {isReconnecting ? (
                  <>
                    <span className="w-3 h-3 rounded-full bg-yellow-400 animate-pulse"></span>
                    <span className="text-sm font-semibold text-white">Connecting...</span>
                  </>
                ) : (
                  <>
                    <span className={`w-3 h-3 rounded-full ${serverOnline ? 'bg-green-400' : 'bg-red-400'} animate-pulse`}></span>
                    <span className="text-sm font-semibold text-white">
                      {serverOnline ? t('lobby.serverOnline') : t('lobby.serverOffline')}
                    </span>
                  </>
                )}
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
        <div className="mb-6 bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 rounded-2xl p-8 text-white shadow-2xl transform hover:scale-105 transition-all duration-300">
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

        {/* Play-to-Earn Info Box */}
        <div className="mb-8 bg-gradient-to-r from-green-500 via-emerald-500 to-teal-500 rounded-xl p-6 text-white shadow-xl">
          <div className="flex items-center justify-between gap-6">
            <div className="flex items-start gap-4 flex-1">
              <div className="w-12 h-12 bg-white bg-opacity-25 rounded-xl flex items-center justify-center backdrop-blur-sm flex-shrink-0">
                <span className="text-3xl">💎</span>
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold mb-2 flex items-center gap-2">
                  Play to Earn Real Money
                  <span className="px-2 py-0.5 bg-yellow-400 text-yellow-900 text-xs font-bold rounded-full animate-pulse">NEW</span>
                </h3>
                <p className="text-sm opacity-95 leading-relaxed">
                  Earn <strong>Gems</strong> by playing and convert them to <strong>real USD</strong> via MTurk! 
                  Your conversations help us research human-AI interaction while you get rewarded. 
                  Win more by being human-like! 🎮💰 Well, it is fake money (MTurk Sandbox) at the moment...
                </p>
              </div>
            </div>
            <button
              onClick={() => navigate('/gems-info')}
              className="flex items-center gap-2 px-5 py-3 bg-white text-green-700 rounded-lg font-bold hover:bg-green-50 transition-all transform hover:scale-105 shadow-lg flex-shrink-0"
            >
              <Award className="w-5 h-5" />
              How It Works
            </button>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white">
            {t('lobby.availableRooms')} ({rooms.length})
          </h2>
          <button
            onClick={() => {
              loadRooms();
              loadAdminRoomStats();
            }}
            disabled={loading}
            className="bg-white bg-opacity-20 text-white px-4 py-2 rounded-lg font-semibold hover:bg-opacity-30 transition-all disabled:opacity-50"
          >
            {loading ? t('lobby.refreshing') : '🔄 ' + t('lobby.refresh')}
          </button>
        </div>

        {/* Admin Room Statistics */}
        {user?.role === 'admin' && adminRoomStats && (
          <div className="mb-6 bg-gradient-to-r from-orange-500 via-red-500 to-pink-500 rounded-xl p-6 shadow-xl">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-white bg-opacity-20 rounded-lg flex items-center justify-center backdrop-blur-sm">
                  <span className="text-2xl">📊</span>
                </div>
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold text-white mb-3">Admin: Operating Rooms</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-white bg-opacity-20 rounded-lg px-4 py-3 backdrop-blur-sm">
                    <div className="text-sm text-white opacity-90 mb-1">Total Operating</div>
                    <div className="text-2xl font-bold text-white">{adminRoomStats.total_operating}</div>
                  </div>
                  <div className="bg-white bg-opacity-20 rounded-lg px-4 py-3 backdrop-blur-sm">
                    <div className="text-sm text-white opacity-90 mb-1">Solo-Human Rooms</div>
                    <div className="text-2xl font-bold text-white">{adminRoomStats.solo_human_count}</div>
                  </div>
                  <div className="bg-white bg-opacity-20 rounded-lg px-4 py-3 backdrop-blur-sm">
                    <div className="text-sm text-white opacity-90 mb-1">Multi-Human Rooms</div>
                    <div className="text-2xl font-bold text-white">{adminRoomStats.multi_human_count}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

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
              <RoomCard 
                key={room.room_code} 
                room={room} 
                onJoin={handleJoinRoom}
                userGemBalance={gemBalance}
              />
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

        {/* Contact Email and Bug Report - Bottom of Page */}
        <div className="flex justify-center items-center gap-2 mt-8 mb-6">
          <a
            href="https://github.com/benchay1999/ai-group-chat-streamlit/issues/new"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-white bg-opacity-10 hover:bg-opacity-20 border border-white border-opacity-20 hover:border-opacity-40 backdrop-blur-md rounded-full transition-all duration-300 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 group"
          >
            <Bug className="w-4 h-4 text-pink-200 group-hover:text-pink-100 transition-transform duration-300 group-hover:rotate-12" />
            <span className="text-sm font-semibold text-pink-100 group-hover:text-white transition-colors">
              Bug report
            </span>
          </a>

          <div className="relative">
            <button
              onClick={() => setShowEmail(!showEmail)}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-white bg-opacity-10 hover:bg-opacity-20 border border-white border-opacity-20 hover:border-opacity-40 backdrop-blur-md rounded-full transition-all duration-300 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 group"
            >
              <Mail className="w-4 h-4 text-blue-200 group-hover:text-white transition-colors" />
              <span className="text-sm font-semibold text-blue-100 group-hover:text-white transition-colors">
                Contact
              </span>
            </button>
            
            {showEmail && (
              <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 inline-flex items-center gap-2 px-4 py-2 bg-white bg-opacity-20 backdrop-blur-sm rounded-full animate-in fade-in slide-in-from-left-2 duration-300 whitespace-nowrap">
                <span className="text-sm font-mono text-white">benchay@kaist.ac.kr</span>
                <button
                  onClick={handleCopyEmail}
                  className="p-1.5 hover:bg-white hover:bg-opacity-20 rounded-full transition-all"
                  title="Copy email"
                >
                  {emailCopied ? (
                    <Check className="w-4 h-4 text-green-300" />
                  ) : (
                    <Copy className="w-4 h-4 text-blue-200 hover:text-white" />
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
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
