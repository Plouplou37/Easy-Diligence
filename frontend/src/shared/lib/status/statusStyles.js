/**
 * One colour tone per status, shared by every screen (badges, text, progress
 * fills, dots). It replaces the per-page maps, which disagreed: `validated`
 * was green on the DD cards but purple in Answer Management, `under_review`
 * purple on one and yellow on the other.
 */

const TONES = {
  neutral: {
    badge: 'bg-surface-hover text-content-secondary border-border',
    text: 'text-content-secondary',
    fill: 'bg-content-muted/40',
    dot: 'bg-content-muted',
  },
  info: {
    badge: 'bg-accent-blue/10 text-accent-blue border-accent-blue/30',
    text: 'text-accent-blue',
    fill: 'bg-primary',
    dot: 'bg-accent-blue',
  },
  warning: {
    badge: 'bg-theme-warning-bg text-theme-warning border-theme-warning-border',
    text: 'text-theme-warning',
    fill: 'bg-theme-warning',
    dot: 'bg-theme-warning',
  },
  success: {
    badge: 'bg-theme-success-bg text-theme-success border-theme-success-border',
    text: 'text-theme-success',
    fill: 'bg-theme-success',
    dot: 'bg-theme-success',
  },
  error: {
    badge: 'bg-theme-error-bg text-theme-error border-theme-error-border',
    text: 'text-theme-error',
    fill: 'bg-theme-error',
    dot: 'bg-theme-error',
  },
  brand: {
    badge: 'bg-primary text-white border-primary',
    text: 'text-content',
    fill: 'bg-primary',
    dot: 'bg-primary',
  },
};

const STATUS_TONES = {
  not_started: 'neutral',
  draft: 'neutral',
  unknown: 'neutral',

  in_progress: 'info',
  generated: 'info',
  manual_edit: 'info',

  paused: 'warning',
  partial: 'warning',
  under_review: 'warning',
  needs_review: 'warning',
  pending: 'warning',

  completed: 'success',
  validated: 'success',
  finalized: 'success',
  approved: 'success',

  failed: 'error',
};

export const TONE_NAMES = Object.keys(TONES);

export const getStatusTone = status =>
  STATUS_TONES[String(status || '').toLowerCase()] || 'neutral';

export const getToneStyles = tone => TONES[tone] || TONES.neutral;

export const getStatusStyles = status => getToneStyles(getStatusTone(status));
