/**
 * Class recipes of the design system, shared by every screen.
 * Plain strings rather than components: pages keep their own markup and
 * behaviour, only the styling is centralised. Colours come from the theme
 * tokens (src/index.css), so none of these need a `dark:` variant.
 */

// Page column: every screen is the same centred width. Some pages ran full
// width (Questions, Vector Stores), others at 6xl or 4xl.
export const pageLayout = {
  container: 'max-w-7xl mx-auto space-y-6',
};

// Page header: small-caps eyebrow, title, gradient hairline.
export const pageHeader = {
  wrapper: 'mb-6',
  eyebrow: 'eyebrow',
  title: 'text-fluid-xl font-medium tracking-tight text-content',
  subtitle: 'mt-1 text-sm text-content-secondary',
  hairline: 'mt-4 h-px hairline-gradient opacity-40',
};

// Section title: uppercase label followed by a hairline.
export const sectionHeader = {
  wrapper: 'flex items-center gap-3',
  title: 'text-fluid-sm font-medium text-content uppercase tracking-[0.18em] whitespace-nowrap',
  hairline: 'flex-1 h-px hairline-gradient opacity-40',
};

// Content panels sitting on the wave background.
export const panel = {
  base: 'relative bg-surface border border-border rounded-lg shadow-sm',
  // Navy-to-gold rail on the left edge of a main card (parent: `relative overflow-hidden`).
  rail: 'absolute inset-y-0 left-0 w-1 side-gradient',
  // Blue-to-green rail, used on stat tiles.
  railBrand: 'absolute inset-y-0 left-0 w-1 side-gradient-2 opacity-70',
  header: 'px-5 py-3.5 border-b border-border',
  body: 'p-5',
  footer: 'px-5 py-3 border-t border-border bg-surface-bg',
};

// Tables: navy header, bordered compact cells, zebra rows.
export const tableStyles = {
  wrapper: 'overflow-x-auto',
  table: 'w-full border-collapse bg-surface text-xs',
  // Add to `table` when it sits inside a bordered panel: drops the outer cell
  // borders that would double the panel's own border.
  inPanel:
    '[&_th:first-child]:border-l-0 [&_td:first-child]:border-l-0 [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0 [&_thead_th]:border-t-0 [&_tbody_tr:last-child_td]:border-b-0',
  thead: 'bg-primary-dark text-white',
  theadSticky: 'bg-primary-dark text-white sticky top-0 z-10',
  th: 'border border-border px-3 h-8 text-left align-middle font-light text-fluid-2xs text-white whitespace-nowrap',
  thCenter:
    'border border-border px-3 h-8 text-center align-middle font-light text-fluid-2xs text-white whitespace-nowrap',
  thRight:
    'border border-border px-3 h-8 text-right align-middle font-light text-fluid-2xs text-white whitespace-nowrap',
  td: 'border border-border px-3 py-2 align-middle text-content',
  tdCenter: 'border border-border px-3 py-2 align-middle text-center text-content',
  tdRight: 'border border-border px-3 py-2 align-middle text-right text-content',
  row: 'transition-colors duration-150 hover:bg-surface-hover',
  rowAlt: index => (index % 2 === 1 ? 'bg-surface-bg' : ''),
  rowSelected: 'bg-accent-blue/10',
  empty: 'border border-border px-3 py-10 text-center text-sm text-content-muted',
};

// The parts of Modal, and its footer for the buttons of a form inside it.
export const modalStyles = {
  panel: 'relative w-full bg-surface border border-border rounded-xl shadow-xl animate-scale-in',
  header: 'flex items-center justify-between px-5 py-3.5 border-b border-border',
  title: 'text-base font-semibold text-content',
  close:
    'p-1 rounded-md text-content-secondary hover:text-content hover:bg-surface-hover transition-colors',
  footer:
    'flex items-center justify-end gap-2 px-5 py-3 border-t border-border bg-surface-bg rounded-b-xl',
};

// Form fields.
export const field = {
  label: 'block text-xs font-medium text-content-secondary mb-1',
  input: 'form-input w-full',
  help: 'mt-1 text-xs text-content-muted',
  error: 'mt-1 text-xs text-theme-error',
};

// Segmented tabs.
export const tabs = {
  group: 'inline-flex rounded-md border border-border overflow-hidden bg-surface',
  tab: 'relative px-3.5 py-1.5 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-bleu-atlantis/40',
  divider: 'border-l border-border',
  active: 'bg-bleu-atlantis/10 text-bleu-atlantis',
  inactive: 'text-content-secondary hover:text-content hover:bg-surface-hover',
  indicator: 'absolute inset-x-0 bottom-0 h-px bg-bleu-atlantis',
};

// Dropdown menus (profile menu, export menu).
export const menu = {
  panel: 'bg-surface border border-border rounded-2xl shadow-lg overflow-hidden',
  header: 'px-4 py-3 border-b border-border',
  item: 'flex w-full items-center gap-2 px-4 py-2.5 text-xs font-medium text-content border-l-2 border-transparent hover:border-bleu-atlantis hover:text-bleu-atlantis transition-colors duration-150',
  itemDanger:
    'flex w-full items-center gap-2 px-4 py-2.5 text-xs font-medium text-content border-l-2 border-transparent hover:border-theme-error hover:text-theme-error transition-colors duration-150',
};

// Empty states.
export const emptyState = {
  wrapper: 'px-4 py-12 text-center',
  icon: 'mx-auto h-10 w-10 text-content-muted',
  title: 'mt-3 text-sm font-medium text-content',
  text: 'mt-1 text-sm text-content-muted',
};
