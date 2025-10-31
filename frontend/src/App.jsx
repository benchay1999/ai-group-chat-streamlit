/**
 * App.jsx
 * Main application component with routing
 */

import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { GameProvider } from './context/GameContext';
import { LanguageProvider } from './context/LanguageContext';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import LobbyPage from './pages/LobbyPage';
import JoinPage from './pages/JoinPage';
import WaitingPage from './pages/WaitingPage';
import GamePage from './pages/GamePage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import SessionDetailPage from './pages/SessionDetailPage';
import AdminPage from './pages/AdminPage';
import AdminAnalyticsPage from './pages/AdminAnalyticsPage';
import ProfilePage from './pages/ProfilePage';
import Wallet from './components/Wallet';
import CashoutConfirm from './pages/CashoutConfirm';

function App() {
  return (
    <AuthProvider>
      <LanguageProvider>
        <GameProvider>
          <Router>
            <Routes>
              {/* Public routes */}
              <Route path="/" element={<Navigate to="/lobby" replace />} />
              <Route path="/lobby" element={<LobbyPage />} />
              <Route path="/join" element={<JoinPage />} />
              <Route path="/waiting" element={<WaitingPage />} />
              <Route path="/game" element={<GamePage />} />
              <Route path="/login" element={<LoginPage />} />
              
              {/* MTurk cashout redemption page (public - accessed from MTurk HIT) */}
              <Route path="/cashout-confirm" element={<CashoutConfirm />} />
              
              {/* Protected routes (require authentication) */}
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <DashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/sessions/:sessionId"
                element={
                  <ProtectedRoute>
                    <SessionDetailPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <ProfilePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/wallet"
                element={
                  <ProtectedRoute>
                    <Wallet />
                  </ProtectedRoute>
                }
              />
              
              {/* Admin routes (require admin role) */}
              <Route
                path="/admin"
                element={
                  <ProtectedRoute requireAdmin={true}>
                    <AdminPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/analytics"
                element={
                  <ProtectedRoute requireAdmin={true}>
                    <AdminAnalyticsPage />
                  </ProtectedRoute>
                }
              />
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
      </LanguageProvider>
    </AuthProvider>
  );
}

export default App;
