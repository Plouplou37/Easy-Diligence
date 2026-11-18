/**
 * Error handling utilities for consistent error management
 */

import { getStatusStyles } from './statusStyles';

/**
 * Handle API errors with consistent logging and user-friendly messages
 * @param {Error} error - The error object
 * @param {string} context - Context where error occurred (e.g., 'Loading data')
 * @param {Object} options - Additional options
 * @param {boolean} options.showToast - Whether to show a toast notification
 * @param {Function} options.onError - Custom error handler
 * @returns {string} User-friendly error message
 */
export const handleApiError = (error, context = 'Operation', options = {}) => {
  const { showToast = false, onError } = options;
  
  let userMessage = 'An unexpected error occurred';
  let logMessage = `${context} failed:`;
  
  if (error.response) {
    // Server responded with error status
    const status = error.response.status;
    const data = error.response.data;
    
    switch (status) {
      case 400:
        userMessage = data.detail || 'Invalid request';
        break;
      case 401:
        userMessage = 'Authentication required';
        break;
      case 403:
        userMessage = 'Access denied';
        break;
      case 404:
        userMessage = 'Resource not found';
        break;
      case 422:
        userMessage = 'Validation error';
        if (data.detail && Array.isArray(data.detail)) {
          userMessage += ': ' + data.detail.map(d => d.msg).join(', ');
        }
        break;
      case 500:
        userMessage = 'Server error - please try again later';
        break;
      default:
        userMessage = `Server error (${status})`;
    }
    
    logMessage += ` ${status} ${data.detail || error.message}`;
  } else if (error.request) {
    // Network error
    userMessage = 'Network error - please check your connection';
    logMessage += ` Network error: ${error.message}`;
  } else {
    // Other error
    userMessage = error.message || userMessage;
    logMessage += ` ${error.message}`;
  }
  
  // Use proper logging instead of console.error
  if (process.env.NODE_ENV === 'development') {
    console.error(logMessage, error);
  }
  
  // Call custom error handler if provided
  if (onError) {
    onError(error, userMessage);
  }
  
  // Show toast notification if requested
  if (showToast && typeof window !== 'undefined' && window.showToast) {
    window.showToast(userMessage, 'error');
  }
  
  return userMessage;
};

/**
 * Create a wrapped API call with error handling
 * @param {Function} apiCall - The API call function
 * @param {string} context - Context for error messages
 * @returns {Function} Wrapped API call
 */
export const withErrorHandling = (apiCall, context) => {
  return async (...args) => {
    try {
      return await apiCall(...args);
    } catch (error) {
      const message = handleApiError(error, context);
      throw new Error(message);
    }
  };
};

/**
 * Normalize status for consistent styling
 * @param {string} status - Status string
 * @returns {string} Normalized lowercase status
 */
export const normalizeStatus = (status) => {
  return status?.toLowerCase() || '';
};

/**
 * Format status for API calls (uppercase)
 * @param {string} status - Status string
 * @returns {string} Uppercase status
 */
export const formatStatusForApi = (status) => {
  return status?.toUpperCase() || '';
};

/**
 * Get status color class for consistent styling
 * @param {string} status - Status string
 * @returns {string} CSS color classes
 */
export const getStatusColor = (status) => getStatusStyles(normalizeStatus(status)).text;

/**
 * Debug logger that only logs in development
 * @param {string} message - Log message
 * @param {any} data - Additional data to log
 */
export const debugLog = (message, data = null) => {
  if (process.env.NODE_ENV === 'development') {
    if (data) {
      console.log(`[DEBUG] ${message}:`, data);
    } else {
      console.log(`[DEBUG] ${message}`);
    }
  }
};