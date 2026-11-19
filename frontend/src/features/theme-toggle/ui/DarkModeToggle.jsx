import { SunIcon, MoonIcon } from '@heroicons/react/24/outline';
import { useTheme } from '@/shared/lib/theme';

const DarkModeToggle = () => {
  const { darkMode, toggleDarkMode } = useTheme();

  return (
    <button
      onClick={toggleDarkMode}
      className="p-1.5 rounded-md text-content-secondary hover:text-content hover:bg-surface-hover transition-colors duration-150"
      aria-label="Toggle dark mode"
    >
      {darkMode ? (
        <SunIcon className="h-5 w-5" />
      ) : (
        <MoonIcon className="h-5 w-5" />
      )}
    </button>
  );
};

export default DarkModeToggle;