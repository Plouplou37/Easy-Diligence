import React from 'react';
import { emptyState } from './styles';

/**
 * Empty state: icon, title, text and an optional action.
 * @param {Object} props
 * @param {React.ComponentType} props.icon - Optional heroicon
 * @param {React.ReactNode} props.title - Main line
 * @param {React.ReactNode} props.text - Optional explanation
 * @param {React.ReactNode} props.action - Optional button(s)
 * @param {string} props.className - Extra classes on the wrapper
 */
export const EmptyState = ({ icon: Icon, title, text, action, className = '' }) => (
  <div className={`${emptyState.wrapper} ${className}`}>
    {Icon && <Icon className={emptyState.icon} />}
    <h3 className={emptyState.title}>{title}</h3>
    {text && <p className={emptyState.text}>{text}</p>}
    {action && <div className="mt-6 flex justify-center gap-2">{action}</div>}
  </div>
);
