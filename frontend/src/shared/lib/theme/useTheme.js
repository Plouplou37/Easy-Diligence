import { useContext } from 'react';
import { ThemeContext } from './context';

/** The theme and its setters of the nearest ThemeProvider. */
export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within a ThemeProvider');
  return context;
};
