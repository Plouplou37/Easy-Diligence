import { useContext } from 'react';
import { AuthContext } from './context';

/** The signed-in user and the account actions of the nearest AuthProvider. */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
