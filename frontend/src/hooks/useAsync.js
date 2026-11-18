import { useState, useCallback } from 'react';

/**
 * Generic hook for handling async operations with loading and error states
 * @param {Function} asyncFunction - The async function to execute
 * @param {boolean} immediate - Whether to execute immediately (default: false)
 * @returns {Object} { data, loading, error, execute, reset }
 *
 * @example
 * const { data, loading, error, execute } = useAsync(
 *   () => sessionAPI.get(sessionId),
 *   true // Execute immediately
 * );
 *
 * // Or execute manually:
 * const { data, loading, execute } = useAsync(() => api.post('/data', payload));
 * // Later: execute();
 */
export const useAsync = (asyncFunction, immediate = false) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);

  const execute = useCallback(
    async (...params) => {
      setLoading(true);
      setError(null);

      try {
        const response = await asyncFunction(...params);
        setData(response);
        return response;
      } catch (err) {
        setError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [asyncFunction]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return {
    data,
    loading,
    error,
    execute,
    reset,
  };
};
