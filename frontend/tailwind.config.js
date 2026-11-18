import typography from '@tailwindcss/typography';

// Each theme colour reads a CSS variable declared in src/index.css (one value
// per theme), while keeping Tailwind's opacity modifier: `bg-surface/60`.
const withAlpha = (cssVar) =>
  `color-mix(in srgb, var(${cssVar}) calc(<alpha-value> * 100%), transparent)`;

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  // The theme is carried by `data-theme` on <html> (set before first paint by
  // index.html). `dark:` variants still present during the migration follow it.
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: withAlpha('--color-surface'),
          hover: withAlpha('--color-surface-hover'),
          elevated: withAlpha('--color-surface-elevated'),
          bg: withAlpha('--color-bg'),
        },
        content: {
          DEFAULT: withAlpha('--color-text'),
          secondary: withAlpha('--color-text-secondary'),
          muted: withAlpha('--color-text-muted'),
          inverse: withAlpha('--color-text-inverse'),
        },
        theme: {
          primary: {
            DEFAULT: withAlpha('--color-primary'),
            light: withAlpha('--color-primary-light'),
            dark: withAlpha('--color-primary-dark'),
          },
          secondary: withAlpha('--color-secondary'),
          success: {
            DEFAULT: withAlpha('--color-success'),
            bg: 'var(--color-success-bg)',
            border: 'var(--color-success-border)',
          },
          warning: {
            DEFAULT: withAlpha('--color-warning'),
            bg: 'var(--color-warning-bg)',
            border: 'var(--color-warning-border)',
          },
          error: {
            DEFAULT: withAlpha('--color-error'),
            bg: 'var(--color-error-bg)',
            border: 'var(--color-error-border)',
          },
        },
        border: {
          DEFAULT: withAlpha('--color-border'),
          hover: withAlpha('--color-border-hover'),
        },
        accent: {
          blue: withAlpha('--color-accent-blue'),
          green: withAlpha('--color-accent-green'),
          deep: withAlpha('--color-accent-deep'),
          gold: withAlpha('--color-accent-gold'),
        },
        primary: {
          DEFAULT: withAlpha('--color-primary'),
          light: withAlpha('--color-primary-light'),
          dark: withAlpha('--color-primary-dark'),
        },
        // Fixed brand colours, identical in both themes.
        bleu: {
          DEFAULT: '#2A4869',
          atlantis: '#3EA0D9',
          lapis: '#1E69AA',
          ciel: '#59A2D9',
          acier: '#45839F',
          fumee: '#85ACC1',
          petrole: '#054253',
        },
        vert: {
          DEFAULT: '#76BB6B',
          prairie: '#76BB6B',
          sauge: '#609591',
        },
        gris: {
          DEFAULT: '#808080',
          light: '#EDEDED',
          extraLight: '#F5F5F5',
        },
        marron: {
          DEFAULT: '#B49B78',
          dark: '#665844',
        },
        or: '#BA9950',
      },
      fontFamily: {
        sans: ['Roboto', 'Arial', 'Helvetica', 'sans-serif'],
      },
      fontSize: {
        'fluid-4xs': ['var(--font-size-fluid-4xs)', { lineHeight: '1.3' }],
        'fluid-3xs': ['var(--font-size-fluid-3xs)', { lineHeight: '1.35' }],
        'fluid-2xs': ['var(--font-size-fluid-2xs)', { lineHeight: '1.45' }],
        'fluid-xs': ['var(--font-size-fluid-xs)', { lineHeight: '1.45' }],
        'fluid-sm': ['var(--font-size-fluid-sm)', { lineHeight: '1.5' }],
        'fluid-md': ['var(--font-size-fluid-md)', { lineHeight: '1.5' }],
        'fluid-lg': ['var(--font-size-fluid-lg)', { lineHeight: '1.35' }],
        'fluid-xl': ['var(--font-size-fluid-xl)', { lineHeight: '1.25' }],
        'fluid-2xl': ['var(--font-size-fluid-2xl)', { lineHeight: '1.2' }],
        'fluid-3xl': ['var(--font-size-fluid-3xl)', { lineHeight: '1.1' }],
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'scale-in': {
          from: { opacity: '0', transform: 'scale(0.95)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 200ms ease-out',
        'scale-in': 'scale-in 200ms ease-out',
      },
      // Markdown (answers, syntheses) follows the theme through the same
      // variables, so `prose` needs no dark variant. Table look: src/index.css.
      typography: {
        DEFAULT: {
          css: {
            '--tw-prose-body': 'var(--color-text)',
            '--tw-prose-headings': 'var(--color-text)',
            '--tw-prose-lead': 'var(--color-text-secondary)',
            '--tw-prose-links': 'var(--color-accent-blue)',
            '--tw-prose-bold': 'var(--color-text)',
            '--tw-prose-counters': 'var(--color-text-muted)',
            '--tw-prose-bullets': 'var(--color-text-muted)',
            '--tw-prose-hr': 'var(--color-border)',
            '--tw-prose-quotes': 'var(--color-text-secondary)',
            '--tw-prose-quote-borders': 'var(--color-accent-blue)',
            '--tw-prose-captions': 'var(--color-text-muted)',
            '--tw-prose-code': 'var(--color-text)',
            '--tw-prose-pre-code': 'var(--color-text)',
            '--tw-prose-pre-bg': 'var(--color-bg)',
            '--tw-prose-th-borders': 'var(--color-border)',
            '--tw-prose-td-borders': 'var(--color-border)',
            '--tw-prose-invert-body': 'var(--color-text)',
            '--tw-prose-invert-headings': 'var(--color-text)',
            '--tw-prose-invert-lead': 'var(--color-text-secondary)',
            '--tw-prose-invert-links': 'var(--color-accent-blue)',
            '--tw-prose-invert-bold': 'var(--color-text)',
            '--tw-prose-invert-counters': 'var(--color-text-muted)',
            '--tw-prose-invert-bullets': 'var(--color-text-muted)',
            '--tw-prose-invert-hr': 'var(--color-border)',
            '--tw-prose-invert-quotes': 'var(--color-text-secondary)',
            '--tw-prose-invert-quote-borders': 'var(--color-accent-blue)',
            '--tw-prose-invert-captions': 'var(--color-text-muted)',
            '--tw-prose-invert-code': 'var(--color-text)',
            '--tw-prose-invert-pre-code': 'var(--color-text)',
            '--tw-prose-invert-pre-bg': 'var(--color-bg)',
            '--tw-prose-invert-th-borders': 'var(--color-border)',
            '--tw-prose-invert-td-borders': 'var(--color-border)',
          },
        },
      },
    },
  },
  plugins: [typography],
}
