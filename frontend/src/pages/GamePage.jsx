/**
 * GamePage
 * Main game interface with WebSocket integration
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGame } from '../context/GameContext';
import { useWebSocket } from '../hooks/useWebSocket';
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
  const { roomCode, playerId, leaveRoom } = useGame();
  
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
  });
  const [typing, setTyping] = useState([]);

  // Redirect if no room/player
  useEffect(() => {
    if (!roomCode || !playerId) {
      navigate('/');
    }
  }, [roomCode, playerId, navigate]);

  // WebSocket message handler
  const handleWebSocketMessage = useCallback((data) => {
    const { type } = data;

    switch (type) {
      case 'message':
        setGameState(prev => ({
          ...prev,
          chat: [...prev.chat, { sender: data.sender, message: data.message }],
        }));
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
        }));
        
        // Update timer based on phase
        if (data.phase === 'Discussion') {
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
        break;

      case 'new_round':
        setGameState(prev => ({
          ...prev,
          round: data.round,
          topic: data.topic,
          phase: 'Discussion',
          timer: 180,
        }));
        toast.success(`Round ${data.round} started!`);
        break;

      case 'room_terminated':
        toast.error('Room was terminated');
        handleLeave();
        break;

      default:
        console.log('Unknown message type:', type);
    }
  }, []);

  // Initialize WebSocket
  const { status: wsStatus } = useWebSocket(roomCode, playerId, handleWebSocketMessage);

  // Timer countdown
  useEffect(() => {
    if (gameState.timer <= 0 || !['Discussion', 'Voting'].includes(gameState.phase)) {
      return;
    }

    const interval = setInterval(() => {
      setGameState(prev => ({
        ...prev,
        timer: Math.max(0, prev.timer - 1),
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
      />
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
          />
        </div>
      </div>
    </div>
  );
};

export default GamePage;

