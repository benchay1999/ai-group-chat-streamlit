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
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setUser(null);
    setIsAuthenticated(false);
    toast.success('Logged out successfully');
  };

  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;

