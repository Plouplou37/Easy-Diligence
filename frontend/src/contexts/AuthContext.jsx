import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import axios from 'axios';
import { API_BASE_URL } from '../config/api.config';

const AuthContext = createContext({});

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
  const navigate = useNavigate();

  useEffect(() => {
    // Check for stored auth data and validate token
    const validateToken = async () => {
      const storedUser = localStorage.getItem('user');
      const token = localStorage.getItem('authToken');
      
      if (storedUser && token) {
        try {
          // Validate token with backend
          const response = await axios.get(`${API_BASE_URL}/api/auth/me`, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });
          
          // Token is valid, set user data (possibly updated)
          const userData = response.data;
          localStorage.setItem('user', JSON.stringify(userData));
          setUser(userData);
        } catch (error) {
          console.error('Token validation failed:', error);
          // Token is invalid, clear auth data
          localStorage.removeItem('user');
          localStorage.removeItem('authToken');
          localStorage.removeItem('refreshToken');
          setUser(null);
        }
      }
      setLoading(false);
    };
    
    validateToken();
  }, []);

  const login = async (email, password) => {
    try {
      // Real API authentication
      
      const response = await axios.post(`${API_BASE_URL}/api/auth/login`, new URLSearchParams({
        username: email, // FastAPI OAuth2PasswordRequestForm expects 'username' field
        password: password
      }), {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });
      
      const { access_token, refresh_token, token_type } = response.data;
      
      // Get user profile with the access token
      const userResponse = await axios.get(`${API_BASE_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${access_token}`,
        },
      });
      
      const userData = userResponse.data;
      
      // Store authentication data
      localStorage.setItem('user', JSON.stringify(userData));
      localStorage.setItem('authToken', access_token);
      localStorage.setItem('refreshToken', refresh_token);
      setUser(userData);
      
      toast.success('Login successful!');
      navigate('/');
      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Login failed';
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  const register = async (name, username, email, password) => {
    try {
      // Real API registration
      
      const response = await axios.post(`${API_BASE_URL}/api/auth/register`, {
        email: email,
        username: username,
        password: password,
        full_name: name
      });
      
      const userData = response.data;
      
      // Auto-login after successful registration
      return await login(email, password);
    } catch (error) {
      console.error('Registration error:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Registration failed';
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  const logout = async () => {
    try {
      const token = localStorage.getItem('authToken');
      
      if (token) {
        // Call backend logout endpoint to invalidate session
        await axios.post(`${API_BASE_URL}/api/auth/logout`, {}, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
      // Continue with local logout even if backend call fails
    } finally {
      // Clear local storage
      localStorage.removeItem('user');
      localStorage.removeItem('authToken');
      localStorage.removeItem('refreshToken');
      setUser(null);
      toast.success('Logged out successfully');
      navigate('/login');
    }
  };

  const updateProfile = async (updates) => {
    try {
      const token = localStorage.getItem('authToken');
      
      if (!token) {
        throw new Error('No authentication token found');
      }

      const response = await axios.put(`${API_BASE_URL}/api/auth/profile`, updates, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
      });
      
      const updatedUser = response.data;
      
      // Update local storage and state with the response from backend
      localStorage.setItem('user', JSON.stringify(updatedUser));
      setUser(updatedUser);
      
      toast.success('Profile updated successfully');
      return { success: true };
    } catch (error) {
      console.error('Update profile error:', error);
      
      let errorMessage = 'Failed to update profile';
      
      if (error.response?.data?.detail) {
        if (Array.isArray(error.response.data.detail)) {
          errorMessage = error.response.data.detail.map(err => err.msg).join(', ');
        } else if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  const changePassword = async (currentPassword, newPassword) => {
    try {
      const token = localStorage.getItem('authToken');
      
      if (!token) {
        throw new Error('No authentication token found');
      }

      await axios.put(`${API_BASE_URL}/api/auth/change-password`, {
        current_password: currentPassword,
        new_password: newPassword
      }, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
      });
      
      toast.success('Password changed successfully! Please log in again.');
      
      // Force logout after password change
      await logout();
      
      return { success: true };
    } catch (error) {
      console.error('Change password error:', error);
      
      let errorMessage = 'Failed to change password';
      
      if (error.response?.data?.detail) {
        // Handle different types of error details
        if (Array.isArray(error.response.data.detail)) {
          // Validation errors from FastAPI
          errorMessage = error.response.data.detail.map(err => err.msg).join(', ');
        } else if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
        } else {
          errorMessage = 'Validation error';
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  const resetPassword = async (email) => {
    try {
      
      await axios.post(`${API_BASE_URL}/api/auth/reset-password`, {
        email: email
      }, {
        headers: {
          'Content-Type': 'application/json'
        },
      });
      
      toast.success('If the email exists, a password reset link has been sent.');
      return { success: true };
    } catch (error) {
      console.error('Reset password error:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to send reset email';
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  // Helper function to get current token
  const getToken = () => {
    return localStorage.getItem('authToken');
  };

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
    isAdmin: user?.role === 'admin'
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;