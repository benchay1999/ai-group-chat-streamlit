/**
 * App.jsx
 * Main application component with routing
 */

import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { GameProvider } from './context/GameContext';
import LobbyPage from './pages/LobbyPage';
import JoinPage from './pages/JoinPage';
import WaitingPage from './pages/WaitingPage';
import GamePage from './pages/GamePage';

function App() {
  return (
    <GameProvider>
      <Router>
        <Routes>
          <Route path="/" element={<LobbyPage />} />
          <Route path="/join" element={<JoinPage />} />
          <Route path="/waiting" element={<WaitingPage />} />
          <Route path="/game" element={<GamePage />} />
        </Routes>
      </Router>
      
      {/* Toast Notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 2000,
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            duration: 4000,
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
    </GameProvider>
  );
}

export default App;
