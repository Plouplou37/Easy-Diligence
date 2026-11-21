import { getToneStyles } from '@/shared/lib/status';

// Historical variant names, plus the tone names of utils/statusStyles so a
// status can be passed through: <Badge variant={getStatusTone(status)}>.
const VARIANT_TONES = {
  success: 'success',
  warning: 'warning',
  error: 'error',
  info: 'info',
  gray: 'neutral',
  neutral: 'neutral',
  brand: 'brand',
};

/**
 * Reusable Badge component for status indicators (chip look)
 * @param {Object} props
 * @param {'success'|'warning'|'error'|'info'|'gray'|'neutral'|'brand'} props.variant - Badge tone
 * @param {'sm'|'md'|'lg'} props.size - Badge size
 * @param {React.ComponentType} props.icon - Optional icon component
 * @param {boolean} props.dot - Show dot indicator
 * @param {React.ReactNode} props.children - Badge content
 */
export const Badge = ({
  variant = 'gray',
  size = 'md',
  icon: Icon,
  dot = false,
  className = '',
  children,
}) => {
  const tone = getToneStyles(VARIANT_TONES[variant] || 'neutral');

  const sizes = {
    sm: 'px-2 py-0.5 text-[0.7rem]',
    md: 'px-2 py-0.5 text-xs',
    lg: 'px-2.5 py-1 text-sm',
  };

  return (
    <span
      className={`inline-flex items-center gap-1 font-semibold rounded-full border whitespace-nowrap ${tone.badge} ${sizes[size] || sizes.md} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${tone.dot}`}></span>}
      {Icon && <Icon className="w-3 h-3" />}
      {children}
    </span>
  );
};
