import { useCallback, useEffect, useMemo, useState } from 'react';
import { ThemeContext } from './context';

// Theme preference: 'light' | 'dark' | 'system', stored under DD_THEME. The
// legacy `darkMode` key ('true'/'false') is still read, so nobody's theme
// changes, but it is no longer written. index.html resolves the theme the same
// way before first paint; the resolved theme lives in `data-theme` on <html>.
const STORAGE_KEY = 'DD_THEME';
const LEGACY_KEY = 'darkMode';

const getSystemTheme = () =>
  window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';

const readStoredMode = () => {
  try {
    const mode = localStorage.getItem(STORAGE_KEY);
    if (mode === 'light' || mode === 'dark' || mode === 'system') return mode;
    const legacy = localStorage.getItem(LEGACY_KEY);
    if (legacy === 'true') return 'dark';
    if (legacy === 'false') return 'light';
  } catch (e) {
    // Storage unavailable: follow the system preference.
  }
  return 'system';
};

const resolveTheme = (mode) => (mode === 'system' ? getSystemTheme() : mode);

const applyTheme = (theme) => {
  document.documentElement.setAttribute('data-theme', theme);
  document.documentElement.style.colorScheme = theme;
};

export const ThemeProvider = ({ children }) => {
  const [mode, setModeState] = useState(readStoredMode);
  const [resolvedTheme, setResolvedTheme] = useState(() => resolveTheme(mode));

  useEffect(() => {
    const theme = resolveTheme(mode);
    setResolvedTheme(theme);
    applyTheme(theme);
  }, [mode]);

  // In system mode, follow OS changes live.
  useEffect(() => {
    if (mode !== 'system') return undefined;
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (event) => {
      const theme = event.matches ? 'dark' : 'light';
      setResolvedTheme(theme);
      applyTheme(theme);
    };
    mql.addEventListener('change', handleChange);
    return () => mql.removeEventListener('change', handleChange);
  }, [mode]);

  const setMode = useCallback((newMode) => {
    setModeState(newMode);
    try {
      localStorage.setItem(STORAGE_KEY, newMode);
    } catch (e) {
      // Not persisted: the choice still applies to this visit.
    }
  }, []);

  const toggleDarkMode = useCallback(() => {
    setMode(resolvedTheme === 'dark' ? 'light' : 'dark');
  }, [resolvedTheme, setMode]);

  const value = useMemo(
    () => ({
      mode,
      resolvedTheme,
      setMode,
      darkMode: resolvedTheme === 'dark',
      toggleDarkMode,
    }),
    [mode, resolvedTheme, setMode, toggleDarkMode]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

