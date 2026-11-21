import { Toaster } from 'react-hot-toast';

// Theme tokens (app/styles/index.css), so toasts follow light and dark mode.
const OPTIONS = {
  duration: 4000,
  style: {
    background: 'var(--color-surface-elevated)',
    color: 'var(--color-text)',
    border: '1px solid var(--color-border-hover)',
    borderRadius: '0.625rem',
    fontSize: '0.875rem',
  },
  success: {
    duration: 3000,
    style: { background: 'var(--color-success)', color: 'var(--color-text-inverse)' },
    iconTheme: { primary: 'var(--color-text-inverse)', secondary: 'var(--color-success)' },
  },
  error: {
    duration: 5000,
    style: { background: 'var(--color-error)', color: 'var(--color-text-inverse)' },
    iconTheme: { primary: 'var(--color-text-inverse)', secondary: 'var(--color-error)' },
  },
};

export const AppToaster = () => <Toaster position="bottom-right" toastOptions={OPTIONS} />;
