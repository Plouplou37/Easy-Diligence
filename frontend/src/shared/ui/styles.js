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

// Page header: title, subtitle, a hairline below.
export const pageHeader = {
  wrapper: 'mb-6',
  eyebrow: 'eyebrow',
  title: 'text-2xl sm:text-[1.75rem] font-bold leading-tight tracking-tight text-content',
  subtitle: 'mt-1.5 text-sm text-content-secondary',
  hairline: 'mt-5 h-px bg-border',
};

// Section title: a small uppercase label followed by a hairline.
export const sectionHeader = {
  wrapper: 'flex items-center gap-3',
  title: 'text-xs font-semibold text-content-muted uppercase tracking-[0.06em] whitespace-nowrap',
  hairline: 'flex-1 h-px bg-border',
};

// Content panels: a plain bordered surface.
export const panel = {
  base: 'relative bg-surface border border-border rounded-xl',
  // Card edges are gone: these stay empty, for the screens that still place them.
  rail: 'hidden',
  railBrand: 'hidden',
  header: 'px-5 py-4 border-b border-border',
  body: 'p-5',
  footer: 'px-5 py-3 border-t border-border bg-surface-bg',
};

// Tables: tinted header, light rules between rows.
export const tableStyles = {
  wrapper: 'overflow-x-auto',
  table: 'w-full border-collapse bg-surface text-sm',
  // Add to `table` when it sits inside a bordered panel: drops the outer cell
  // borders that would double the panel's own border.
  inPanel:
    '[&_th:first-child]:border-l-0 [&_td:first-child]:border-l-0 [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0 [&_thead_th]:border-t-0 [&_tbody_tr:last-child_td]:border-b-0',
  thead: 'bg-surface-hover text-content-secondary',
  theadSticky: 'bg-surface-hover text-content-secondary sticky top-0 z-10',
  th: 'border-b border-border px-3 h-10 text-left align-middle font-semibold text-xs text-content-secondary whitespace-nowrap',
  thCenter:
    'border-b border-border px-3 h-10 text-center align-middle font-semibold text-xs text-content-secondary whitespace-nowrap',
  thRight:
    'border-b border-border px-3 h-10 text-right align-middle font-semibold text-xs text-content-secondary whitespace-nowrap',
  td: 'border-b border-border px-3 py-2.5 align-middle text-content',
  tdCenter: 'border-b border-border px-3 py-2.5 align-middle text-center text-content',
  tdRight: 'border-b border-border px-3 py-2.5 align-middle text-right text-content',
  row: 'transition-colors duration-150 hover:bg-surface-hover',
  rowAlt: () => '',
  rowSelected: 'bg-primary-dark',
  empty: 'px-3 py-10 text-center text-sm text-content-muted',
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
  label: 'block text-sm font-medium text-content mb-1.5',
  input: 'form-input w-full',
  help: 'mt-1.5 text-xs text-content-muted',
  error: 'mt-1.5 text-xs text-theme-error',
};

// Segmented tabs.
export const tabs = {
  group: 'inline-flex gap-1 p-1 rounded-lg border border-border bg-surface-bg',
  tab: 'relative px-3.5 py-1.5 rounded-md text-sm font-semibold transition-colors focus:outline-hidden focus-visible:ring-2 focus-visible:ring-accent-blue/60',
  divider: '',
  active: 'bg-surface-hover text-content',
  inactive: 'text-content-secondary hover:text-content',
  indicator: 'hidden',
};

// Dropdown menus (profile menu).
export const menu = {
  panel: 'bg-surface-elevated border border-border rounded-xl shadow-lg overflow-hidden',
  header: 'px-4 py-3 border-b border-border',
  item: 'flex w-full items-center gap-2 px-4 py-2.5 text-sm font-medium text-content hover:bg-surface-hover transition-colors duration-150',
  itemDanger:
    'flex w-full items-center gap-2 px-4 py-2.5 text-sm font-medium text-content hover:bg-theme-error-bg hover:text-theme-error transition-colors duration-150',
};

// Empty states.
export const emptyState = {
  wrapper: 'px-4 py-12 text-center',
  icon: 'mx-auto h-10 w-10 text-content-muted',
  title: 'mt-3 text-sm font-medium text-content',
  text: 'mt-1 text-sm text-content-muted',
};
