import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { authAPI, errorMessage } from '../services/api';

const AuthContext = createContext({});

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

const storeSession = (user, accessToken, refreshToken) => {
  localStorage.setItem('user', JSON.stringify(user));
  if (accessToken) localStorage.setItem('authToken', accessToken);
  if (refreshToken) localStorage.setItem('refreshToken', refreshToken);
};

const clearSession = () => {
  localStorage.removeItem('user');
  localStorage.removeItem('authToken');
  localStorage.removeItem('refreshToken');
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  // A stored token is checked against the backend on start.
  useEffect(() => {
    const restore = async () => {
      if (localStorage.getItem('authToken')) {
        try {
          const { data } = await authAPI.me();
          storeSession(data);
          setUser(data);
        } catch {
          clearSession();
          setUser(null);
        }
      }
      setLoading(false);
    };
    restore();
  }, []);

  const login = async (email, password) => {
    try {
      const { data: tokens } = await authAPI.login(email, password);
      localStorage.setItem('authToken', tokens.access_token);
      const { data: profile } = await authAPI.me();
      storeSession(profile, tokens.access_token, tokens.refresh_token);
      setUser(profile);
      toast.success('Login successful!');
      navigate('/');
      return { success: true };
    } catch (error) {
      clearSession();
      const message = errorMessage(error, 'Login failed');
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const register = async (name, username, email, password) => {
    try {
      await authAPI.register({ email, username, password, full_name: name });
      return await login(email, password);
    } catch (error) {
      const message = errorMessage(error, 'Registration failed');
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const logout = async () => {
    try {
      if (localStorage.getItem('authToken')) {
        await authAPI.logout();
      }
    } catch {
      // Logged out here anyway, even if the backend could not be told.
    } finally {
      clearSession();
      setUser(null);
      toast.success('Logged out successfully');
      navigate('/login');
    }
  };

  const updateProfile = async (updates) => {
    try {
      const { data } = await authAPI.updateProfile(updates);
      storeSession(data);
      setUser(data);
      toast.success('Profile updated successfully');
      return { success: true };
    } catch (error) {
      const message = errorMessage(error, 'Failed to update profile');
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const changePassword = async (currentPassword, newPassword) => {
    try {
      await authAPI.changePassword(currentPassword, newPassword);
      toast.success('Password changed successfully! Please log in again.');
      // Every session is closed by the backend: log in again.
      await logout();
      return { success: true };
    } catch (error) {
      const message = errorMessage(error, 'Failed to change password');
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const resetPassword = async (email) => {
    try {
      await authAPI.requestPasswordReset(email);
      toast.success('If the email exists, a password reset link has been sent.');
      return { success: true };
    } catch (error) {
      const message = errorMessage(error, 'Failed to send reset email');
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const getToken = () => localStorage.getItem('authToken');

  const value = {
    user,
    loading,
    login,
    register,
    logout,
    updateProfile,
    changePassword,
    resetPassword,
    getToken,
    token: getToken(),
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;
