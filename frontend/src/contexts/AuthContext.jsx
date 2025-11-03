/**
 * Authentication Context
 * Manages global authentication state and provides auth functions
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/authAPI';
import toast from 'react-hot-toast';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Load user from localStorage on mount
  useEffect(() => {
    const loadUser = async () => {
      const token = localStorage.getItem('access_token');
      const savedUser = localStorage.getItem('user');

      if (token && savedUser) {
        try {
          // Verify token is still valid by fetching current user
          const userData = await authAPI.getCurrentUser();
          setUser(userData);
          setIsAuthenticated(true);
        } catch (error) {
          // Token invalid or expired
          console.error('Failed to load user:', error);
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          setUser(null);
          setIsAuthenticated(false);
        }
      }
      setLoading(false);
    };

    loadUser();
  }, []);

  // Listen for logout events from other tabs
  useEffect(() => {
    const handleStorageChange = (e) => {
      // Only use the explicit logout_event for cross-tab synchronization
      // This prevents duplicate processing when multiple storage events fire
      if (e.key === 'logout_event' && e.newValue) {
        console.log('Logout detected from another tab');
        
        // Clear all auth and session data from localStorage
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        localStorage.removeItem('mturk_context');
        localStorage.removeItem('ai-group-chat-active-session'); // Clear active game session
        
        // Update authentication state
        setUser(null);
        setIsAuthenticated(false);
        
        // Notify user
        toast.info('You have been logged out from another tab');
      }
    };

    // Add storage event listener (only fires for changes from other tabs)
    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  const login = async (userId, password) => {
    try {
      const data = await authAPI.login(userId, password);
      
      // Save token and user to localStorage
      localStorage.setItem('access_token', data.access_token);
      const userData = {
        user_id: data.user_id,
        role: data.role,
      };
      localStorage.setItem('user', JSON.stringify(userData));

      // Fetch full user data
      const fullUserData = await authAPI.getCurrentUser();
      setUser(fullUserData);
      setIsAuthenticated(true);

      toast.success(`Welcome back, ${data.user_id}!`);
      return { success: true };
    } catch (error) {
      const message = error.response?.data?.detail || 'Login failed';
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const register = async (userId, password) => {
    try {
      await authAPI.register(userId, password);
      toast.success('Registration successful! Please log in.');
      return { success: true };
    } catch (error) {
      const message = error.response?.data?.detail || 'Registration failed';
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const logout = () => {
    // Clear all auth and session data
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    localStorage.removeItem('mturk_context');
    localStorage.removeItem('ai-group-chat-active-session'); // Clear active game session
    
    // Trigger logout event for other tabs
    // Use timestamp to ensure the event always fires (different value each time)
    localStorage.setItem('logout_event', Date.now().toString());
    localStorage.removeItem('logout_event');
    
    // Update state in current tab
    setUser(null);
    setIsAuthenticated(false);
    toast.success('Logged out successfully');
  };

  const mturkLogin = async (workerId, assignmentId, hitId) => {
    try {
      const data = await authAPI.mturkRegister(workerId, assignmentId, hitId);
      
      // Check if preview mode
      if (data.preview_mode) {
        return { success: false, preview_mode: true, message: data.message };
      }
      
      // Save token and user to localStorage
      localStorage.setItem('access_token', data.access_token);
      const userData = {
        user_id: data.user_id,
        role: data.role,
        is_mturk_worker: true,
      };
      localStorage.setItem('user', JSON.stringify(userData));
      
      // Save MTurk context for session tracking
      localStorage.setItem('mturk_context', JSON.stringify(data.mturk_context));

      // Fetch full user data
      const fullUserData = await authAPI.getCurrentUser();
      setUser({ ...fullUserData, is_mturk_worker: true });
      setIsAuthenticated(true);

      toast.success(`Welcome, MTurk Worker! 🎯`);
      return { success: true, mturk_context: data.mturk_context };
    } catch (error) {
      const message = error.response?.data?.detail || 'MTurk authentication failed';
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    register,
    logout,
    mturkLogin,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;

