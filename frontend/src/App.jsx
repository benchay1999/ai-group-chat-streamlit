/**
 * App.jsx
 * Main application component with routing
 */

import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { GameProvider } from './contexts/GameContext';
import { LanguageProvider } from './contexts/LanguageContext';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import ErrorBoundary from './components/ErrorBoundary';
import ActiveSessionGuard from './components/ActiveSessionGuard';
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
import LeaderboardPage from './pages/LeaderboardPage';
import GemsInfoPage from './pages/GemsInfoPage';

function App() {
  return (
    <AuthProvider>
      <LanguageProvider>
        <GameProvider>
          <Router>
            <ActiveSessionGuard>
            <Routes>
              {/* Public routes */}
              <Route path="/" element={<Navigate to="/lobby" replace />} />
              <Route path="/lobby" element={<LobbyPage />} />
              <Route path="/leaderboard" element={<LeaderboardPage />} />
              <Route path="/gems-info" element={<GemsInfoPage />} />
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
                    <ErrorBoundary>
                      <DashboardPage />
                    </ErrorBoundary>
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
            </ActiveSessionGuard>
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
