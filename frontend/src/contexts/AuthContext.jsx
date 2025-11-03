/**
 * Authentication Context
 * Manages global authentication state and provides auth functions
 */

import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
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
  
  // Use ref to access current user without triggering effect re-runs
  const userRef = useRef(null);
  
  // Keep ref in sync with state
  useEffect(() => {
    userRef.current = user;
  }, [user]);

  /**
   * Centralized function to clear all authentication-related data
   * Ensures consistency across logout, force logout, and error scenarios
   */
  const clearAuthData = () => {
    // Clear all auth and session data from localStorage
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    localStorage.removeItem('mturk_context');
    localStorage.removeItem('ai-group-chat-active-session');
    
    // Clear authentication state
    setUser(null);
    setIsAuthenticated(false);
  };

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
          clearAuthData();
        }
      }
      setLoading(false);
    };

    loadUser();
  }, []);

  // Listen for auth events from other tabs (login/logout synchronization)
  useEffect(() => {
    const handleStorageChange = (e) => {
      // Handle logout events from other tabs
      if (e.key === 'logout_event' && e.newValue) {
        console.log('Logout detected from another tab');
        
        // Clear all auth data using centralized function
        clearAuthData();
        
        // Notify user
        toast.info('You have been logged out from another tab');
      }
      
      // Handle login events from other tabs
      // Enforce single user per browser - if different user logs in, log out current user
      if (e.key === 'login_event' && e.newValue) {
        console.log('Login detected from another tab');
        
        try {
          const loginData = JSON.parse(e.newValue);
          // Use userRef to get current user without stale closure issues
          const currentUserId = userRef.current?.user_id;
          const newUserId = loginData.user_id;
          
          // If current tab has a different user logged in, force logout
          if (currentUserId && newUserId && currentUserId !== newUserId) {
            console.log(`Different user login detected: ${currentUserId} -> ${newUserId}`);
            
            // CRITICAL: Clear ALL auth data to prevent security vulnerabilities
            clearAuthData();
            
            // Notify user that they were logged out
            toast.info(`Another user (${newUserId}) logged in. You have been logged out.`);
          }
          // If no user is logged in this tab, sync with the new login
          else if (!currentUserId && newUserId) {
            console.log(`Syncing login from another tab: ${newUserId}`);
            
            // Reload user data to sync with the new login
            const loadUserFromStorage = async () => {
              const token = localStorage.getItem('access_token');
              const savedUser = localStorage.getItem('user');
              
              if (token && savedUser) {
                try {
                  const userData = await authAPI.getCurrentUser();
                  setUser(userData);
                  setIsAuthenticated(true);
                  toast.success(`Logged in as ${userData.user_id} (from another tab)`);
                } catch (error) {
                  console.error('Failed to sync login from another tab:', error);
                  
                  // CRITICAL: If sync fails, clear inconsistent state
                  clearAuthData();
                  
                  toast.error('Failed to sync login. Please log in again.');
                }
              }
            };
            loadUserFromStorage();
          }
          // If same user logs in again (re-login), just ensure state is consistent
          else if (currentUserId && newUserId && currentUserId === newUserId) {
            console.log(`Same user re-logged in: ${newUserId}`);
            // No action needed - user is already logged in with correct credentials
            // This prevents unnecessary toast notifications for re-logins
          }
        } catch (error) {
          console.error('Error parsing login event:', error);
          // Don't crash on corrupted login events - just log and ignore
        }
      }
    };

    // Add storage event listener (only fires for changes from other tabs)
    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []); // No dependencies - use userRef.current to access user without re-running effect

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

      // Broadcast login event to other tabs
      // Use timestamp to ensure the event always fires (different value each time)
      const loginEvent = JSON.stringify({
        user_id: data.user_id,
        timestamp: Date.now()
      });
      localStorage.setItem('login_event', loginEvent);
      localStorage.removeItem('login_event');

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
    // Clear all auth and session data using centralized function
    clearAuthData();
    
    // Trigger logout event for other tabs
    // Use timestamp to ensure the event always fires (different value each time)
    localStorage.setItem('logout_event', Date.now().toString());
    localStorage.removeItem('logout_event');
    
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

      // Broadcast login event to other tabs
      // Use timestamp to ensure the event always fires (different value each time)
      const loginEvent = JSON.stringify({
        user_id: data.user_id,
        timestamp: Date.now()
      });
      localStorage.setItem('login_event', loginEvent);
      localStorage.removeItem('login_event');

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

