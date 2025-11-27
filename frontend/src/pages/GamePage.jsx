/**
 * GamePage
 * Main game interface with WebSocket integration
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGame } from '../context/GameContext';
import { useWebSocket } from '../hooks/useWebSocket';
import { useHeartbeat } from '../hooks/useHeartbeat';
import { roomAPI } from '../services/api';
import PlayerList from '../components/PlayerList';
import ChatWindow from '../components/ChatWindow';
import MessageInput from '../components/MessageInput';
import ConnectionStatus from '../components/ConnectionStatus';
import PhaseTimer from '../components/PhaseTimer';
import GameOver from '../components/GameOver';
import toast from 'react-hot-toast';

const GamePage = () => {
  const navigate = useNavigate();
  const { roomCode, playerId, leaveRoom, saveActiveSession, clearActiveSession } = useGame();
  
  // Loading state to prevent rendering child components before initial state is loaded
  const [isLoadingInitialState, setIsLoadingInitialState] = useState(true);

  const [gameState, setGameState] = useState({
    phase: 'Discussion',
    round: 1,
    topic: '',
    players: [],
    chat: [],
    timer: 180,
    winner: null,
    selected_suspect: null,
    suspect_role: null,
    num_human_players: 1,  // Default to 1, updated by backend
  });
  const [typing, setTyping] = useState([]);

  // Send heartbeat to track this user as online
  useHeartbeat();

  // Save active session when component mounts (user is in game)
  useEffect(() => {
    if (roomCode && playerId) {
      saveActiveSession(roomCode, playerId, 'in_progress');
    }
  }, [roomCode, playerId, saveActiveSession]);

  // Redirect if no room/player
  useEffect(() => {
    // Allow a grace period for session restoration
    const timer = setTimeout(() => {
      if (!roomCode || !playerId) {
        // Check if we have a saved session in localStorage that might be restoring
        const savedSession = localStorage.getItem('ai-group-chat-active-session');
        if (!savedSession) {
          navigate('/');
        }
      }
    }, 1000);
    
    return () => clearTimeout(timer);
  }, [roomCode, playerId, navigate]);

  // Fetch initial game state including chat history
  useEffect(() => {
    const fetchGameState = async () => {
      if (!roomCode || !playerId) return;

      try {
        console.log('📥 Fetching initial game state...');
        const state = await roomAPI.getGameState(roomCode, playerId);
        
        if (state.exists) {
          setGameState(prev => ({
            ...prev,
            phase: state.phase,
            round: state.round,
            topic: state.topic,
            players: state.players,
            // Merge chat history, respecting timestamps if available
            chat: state.chat_history || [],
            winner: state.winner,
            selected_suspect: state.selected_suspect,
            suspect_role: state.suspect_role,
            vote_counts: state.vote_counts,
            // Calculate timer based on phase if needed
            timer: state.phase === 'Discussion' ? (state.timer || 180) : (state.timer || 60)
          }));
          
          // Check if current player has already voted
          // The players array from backend already has 'voted' property set correctly
          // based on: "voted": p['id'] in state.get('votes', {})
          const currentPlayer = state.players.find(p => p.id === playerId);
          if (currentPlayer && currentPlayer.voted) {
            console.log('✅ Player has already voted, restoring state');
          }
          
          console.log('✅ Initial game state loaded:', state);
        }
      } catch (error) {
        console.error('Error fetching game state:', error);
        // Don't show error toast as WebSocket will likely connect and work anyway
      } finally {
        setIsLoadingInitialState(false);
      }
    };

    fetchGameState();
  }, [roomCode, playerId]);

  // Helper to check for duplicate messages
  const isDuplicateMessage = (existingChat, newMessage) => {
    // If we have timestamps, use them for precise deduping
    if (newMessage.timestamp) {
      return existingChat.some(msg => 
        msg.timestamp === newMessage.timestamp && 
        msg.sender === newMessage.sender
      );
    }
    
    // Fallback: Check last few messages for identical content/sender
    // This prevents duplicates if timestamp is missing but allows same message later
    const recentMessages = existingChat.slice(-5);
    return recentMessages.some(msg => 
      msg.sender === newMessage.sender && 
      msg.message === newMessage.message
    );
  };

  // WebSocket message handler
  const handleWebSocketMessage = useCallback((data) => {
    const { type } = data;

    switch (type) {
      case 'message':
        setGameState(prev => {
          // Check for duplicates before adding
          if (isDuplicateMessage(prev.chat, data)) {
            console.log('Start duplicate check');
            return prev;
          }
          
          return {
            ...prev,
            chat: [...prev.chat, { 
              sender: data.sender, 
              message: data.message,
              timestamp: data.timestamp 
            }],
          };
        });
        break;


      case 'typing':
        setTyping(prev => {
          if (data.status === 'start') {
            return [...new Set([...prev, data.player])];
          } else {
            return prev.filter(p => p !== data.player);
          }
        });
        break;

      case 'phase':
        setGameState(prev => ({
          ...prev,
          phase: data.phase,
          players: prev.players.map(p => ({ ...p, voted: false })),
          num_human_players: data.num_human_players || prev.num_human_players,  // Update from backend
        }));
        
        // Update timer based on phase duration from server
        if (data.phase === 'Discussion' && data.discussion_duration) {
          setGameState(prev => ({ ...prev, timer: data.discussion_duration }));
        } else if (data.phase === 'Voting' && data.voting_duration) {
          setGameState(prev => ({ ...prev, timer: data.voting_duration }));
        } else if (data.phase === 'Discussion') {
          // Fallback to default if not provided
          setGameState(prev => ({ ...prev, timer: 180 }));
        } else if (data.phase === 'Voting') {
          setGameState(prev => ({ ...prev, timer: 60 }));
        }
        
        toast.success(`Phase: ${data.phase}`);
        break;

      case 'topic':
        setGameState(prev => ({ ...prev, topic: data.topic }));
        break;

      case 'player_list':
        setGameState(prev => ({
          ...prev,
          players: data.players.map(id => ({ id, voted: false, eliminated: false })),
        }));
        break;

      case 'voted':
        setGameState(prev => ({
          ...prev,
          players: prev.players.map(p => 
            p.id === data.player ? { ...p, voted: true } : p
          ),
        }));
        break;

      case 'elimination':
        setGameState(prev => ({
          ...prev,
          players: prev.players.map(p =>
            p.id === data.eliminated ? { ...p, eliminated: true } : p
          ),
        }));
        toast(`${data.eliminated} was eliminated (${data.role})`);
        break;

      case 'voting_result':
        setGameState(prev => ({
          ...prev,
          selected_suspect: data.suspect,
          suspect_role: data.role,
          vote_counts: data.vote_counts,
        }));
        break;

      case 'game_over':
        setGameState(prev => ({
          ...prev,
          winner: data.winner,
          phase: 'Game Over',
        }));
        // Clear active session when game ends
        clearActiveSession();
        break;

      case 'new_round':
        setGameState(prev => ({
          ...prev,
          round: data.round,
          topic: data.topic,
          phase: 'Discussion',
          timer: data.discussion_duration || 180,  // Use server duration or fallback
        }));
        toast.success(`Round ${data.round} started!`);
        break;

      case 'room_terminated':
        toast.error('Room was terminated');
        // Clear active session when room is terminated
        clearActiveSession();
        handleLeave();
        break;

      case 'system_message':
        // Display system/error messages in chat
        setGameState(prev => ({
          ...prev,
          chat: [...prev.chat, { 
            sender: '⚠️ SYSTEM', 
            message: data.message,
            isSystem: true,
            severity: data.severity || 'info'
          }],
        }));
        
        // Also show as toast based on severity
        if (data.severity === 'error') {
          toast.error(data.message);
        } else {
          toast.info(data.message);
        }
        break;

      case 'gem_rewards':
        // Store gem rewards for display in game over screen
        setGameState(prev => ({
          ...prev,
          gem_rewards: data.rewards,
        }));
        console.log('💎 Received gem rewards:', data.rewards);
        break;

      case 'timer_sync':
        // Server-synchronized timer update (every 5 seconds)
        setGameState(prev => ({
          ...prev,
          timer: data.time_remaining,
          serverSynced: true,
        }));
        break;

      case 'error':
        toast.error(data.message);
        break;

      default:
        console.log('Unknown message type:', type);
    }
  }, [clearActiveSession]);

  // Initialize WebSocket
  const { status: wsStatus, sendMessage: wsSendMessage } = useWebSocket(roomCode, playerId, handleWebSocketMessage);

  // Timer countdown (client-side, gets synced with server every 5 seconds)
  useEffect(() => {
    if (gameState.timer <= 0 || !['Discussion', 'Voting'].includes(gameState.phase)) {
      return;
    }

    const interval = setInterval(() => {
      setGameState(prev => ({
        ...prev,
        timer: Math.max(0, prev.timer - 1),
        serverSynced: false,  // Mark as client-calculated until next server sync
      }));
    }, 1000);

    return () => clearInterval(interval);
  }, [gameState.timer, gameState.phase]);

  // Send message
  const handleSendMessage = async (message) => {
    try {
      // Send via REST API - WebSocket will handle UI update
      await roomAPI.sendMessage(roomCode, playerId, message);
    } catch (error) {
      console.error('Error sending message:', error);
      toast.error('Failed to send message');
    }
  };

  // Handle typing indicator
  const handleTypingChange = (status) => {
    // Only send typing indicators during Discussion phase
    if (gameState.phase !== 'Discussion') {
      return;
    }
    
    // Send typing status via WebSocket
    if (wsSendMessage) {
      wsSendMessage({
        type: 'typing',
        status: status
      });
    }
  };

  // Cast vote
  const handleCastVote = async (votedFor) => {
    try {
      await roomAPI.castVote(roomCode, playerId, votedFor);
      
      // Update local state
      setGameState(prev => ({
        ...prev,
        players: prev.players.map(p =>
          p.id === playerId ? { ...p, voted: true } : p
        ),
      }));
      
      toast.success(`Voted for ${votedFor}`);
    } catch (error) {
      console.error('Error casting vote:', error);
      toast.error(error.response?.data?.error || 'Failed to cast vote');
    }
  };

  // Leave room
  const handleLeave = async () => {
    try {
      await roomAPI.leaveRoom(roomCode, playerId);
    } catch (error) {
      console.error('Error leaving room:', error);
    }
    
    // Clear active session when explicitly leaving
    clearActiveSession();
    leaveRoom();
    navigate('/');
  };

  const getPhaseColor = () => {
    switch (gameState.phase) {
      case 'Discussion':
        return 'from-green-500 to-emerald-600';
      case 'Voting':
        return 'from-yellow-500 to-orange-600';
      case 'Game Over':
        return 'from-purple-500 to-pink-600';
      default:
        return 'from-gray-500 to-gray-600';
    }
  };

  // Game Over screen
  if (gameState.winner) {
    const voteCountsDisplay = gameState.vote_counts
      ? Object.entries(gameState.vote_counts).map(([player, votes]) => ({
          player,
          votes,
        }))
      : [];

    return (
      <GameOver
        winner={gameState.winner}
        suspect={gameState.selected_suspect}
        suspectRole={gameState.suspect_role}
        voteCountsDisplay={voteCountsDisplay}
        onLeave={handleLeave}
        roomCode={roomCode}
        gemRewards={gameState.gem_rewards}
        playerId={playerId}
      />
    );
  }

  // Show loading state while fetching initial game state
  if (isLoadingInitialState) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-900 text-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-purple-500 mx-auto mb-4"></div>
          <p className="text-lg">Loading game state...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Header */}
      <div className={`bg-gradient-to-r ${getPhaseColor()} text-white shadow-lg`}>
        <div className="max-w-full mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div>
                <h1 className="text-2xl font-bold">Group Chat</h1>
                <p className="text-sm opacity-90">Room: {roomCode}</p>
              </div>
              <div className="hidden md:flex items-center gap-4">
                <div className="bg-white bg-opacity-20 rounded-lg px-4 py-2">
                  <span className="text-xs opacity-75">Round</span>
                  <p className="text-xl font-bold">{gameState.round}</p>
                </div>
                <div className="bg-white bg-opacity-20 rounded-lg px-4 py-2">
                  <span className="text-xs opacity-75">Phase</span>
                  <p className="text-xl font-bold">{gameState.phase}</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              {['Discussion', 'Voting'].includes(gameState.phase) && (
                <PhaseTimer initialTime={gameState.timer} phase={gameState.phase} />
              )}
              <ConnectionStatus status={wsStatus} />
            </div>
          </div>
          
          {/* Topic */}
          {gameState.topic && (
            <div className="mt-3 bg-white bg-opacity-20 rounded-lg px-4 py-2">
              <span className="text-xs opacity-75">Topic: </span>
              <span className="font-semibold">{gameState.topic}</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Player List Sidebar */}
        <PlayerList
          players={gameState.players}
          phase={gameState.phase}
          castVote={handleCastVote}
          currentPlayerId={playerId}
          onLeave={handleLeave}
          numHumanPlayers={gameState.num_human_players}
        />

        {/* Chat Area */}
        <div className="flex-1 flex flex-col">
          <ChatWindow
            chat={gameState.chat}
            typing={typing}
            currentPlayerId={playerId}
          />
          <MessageInput
            onSendMessage={handleSendMessage}
            disabled={gameState.phase !== 'Discussion'}
            phase={gameState.phase}
            onTypingChange={handleTypingChange}
          />
        </div>
      </div>
    </div>
  );
};

export default GamePage;

