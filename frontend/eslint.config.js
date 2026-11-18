// ESLint (flat config). The same rules as before the move to ESLint 9, except:
// - dist/ (the build output) is not linted;
// - react/prop-types is off: the code uses no PropTypes, so the rule only
//   produced noise (379 warnings).
// And the Feature-Sliced Design layers (eslint-plugin-boundaries): a layer
// imports only the layers below it, and a slice never imports another slice
// of its own layer.
import { fileURLToPath } from 'node:url';

import js from '@eslint/js';
import boundaries from 'eslint-plugin-boundaries';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import globals from 'globals';

// app > pages > widgets > features > entities > shared
const SLICED = ['pages', 'widgets', 'features', 'entities'];
const layer = (type) => ({ to: { element: { type } } });
const below = (types) => types.map(layer);
const sameSlice = (type) => ({
  to: { element: { type, captured: { slice: '{{ from.element.captured.slice }}' } } },
});

const LAYERS = [
  { from: 'app', allow: below(['app', ...SLICED, 'shared']) },
  { from: 'pages', allow: [sameSlice('pages'), ...below(['widgets', 'features', 'entities', 'shared'])] },
  { from: 'widgets', allow: [sameSlice('widgets'), ...below(['features', 'entities', 'shared'])] },
  { from: 'features', allow: [sameSlice('features'), ...below(['entities', 'shared'])] },
  { from: 'entities', allow: [sameSlice('entities'), layer('shared')] },
  { from: 'shared', allow: [layer('shared')] },
];

export default [
  { ignores: ['dist'] },
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    settings: {
      react: { version: 'detect' },
      // "@/" is "src/" (vite.config.js).
      'import/resolver': {
        [fileURLToPath(new URL('./eslint-alias-resolver.cjs', import.meta.url))]: {},
      },
      'boundaries/elements': [
        { type: 'app', pattern: 'src/app' },
        ...SLICED.map((type) => ({ type, pattern: `src/${type}/*`, capture: ['slice'] })),
        { type: 'shared', pattern: 'src/shared' },
      ],
    },
    plugins: {
      boundaries,
      react,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...js.configs.recommended.rules,
      ...react.configs.recommended.rules,
      ...react.configs['jsx-runtime'].rules,
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      'react/prop-types': 'off',
      'react-refresh/only-export-components': 'warn',
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      // caughtErrors: as with ESLint 8, an unused `catch (error)` is not reported.
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_', caughtErrors: 'none' }],
      'boundaries/dependencies': [
        'error',
        {
          default: 'disallow',
          policies: LAYERS.map(({ from, allow }) => ({ from: { element: { type: from } }, allow })),
        },
      ],
    },
  },
  {
    // Build configuration, run by Node.
    files: ['*.config.js', '*.cjs'],
    languageOptions: { globals: globals.node },
  },
];
