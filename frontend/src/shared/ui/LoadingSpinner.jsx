const LOGO_WIDTHS = {
  lg: 'clamp(160px, 22vw, 280px)',
  xl: 'clamp(240px, 40vw, 520px)',
};

// App logo used as a mask, filled by the blue-to-green sweep (loading overlay).
const renderLogoShimmer = width => (
  <div
    className="logo-shimmer-animate"
    style={{
      width,
      aspectRatio: '640 / 100',
      WebkitMask: "url('/logo-white.svg') no-repeat center / contain",
      mask: "url('/logo-white.svg') no-repeat center / contain",
    }}
  />
);

/**
 * Reusable Loading Spinner component
 * sm / md: thin accent ring. lg / xl and fullPage: logo shimmer.
 * @param {Object} props
 * @param {'sm'|'md'|'lg'|'xl'} props.size - Spinner size
 * @param {string} props.text - Optional loading text
 * @param {boolean} props.fullPage - Show as full-page overlay
 * @param {boolean} props.inline - Inline display (no centering)
 */
export const LoadingSpinner = ({
  size = 'md',
  text,
  fullPage = false,
  inline = false,
  className = '',
}) => {
  const rings = {
    sm: 'h-4 w-4 border-2',
    md: 'h-7 w-7 border-2',
  };

  const useLogo = fullPage || size === 'lg' || size === 'xl';

  const spinner = (
    <>
      {useLogo ? (
        renderLogoShimmer(LOGO_WIDTHS[size] || LOGO_WIDTHS.lg)
      ) : (
        <div
          className={`animate-spin rounded-full border-accent-blue/25 border-t-accent-blue ${rings[size] || rings.md}`}
        />
      )}
      {text && (
        <p className="mt-3 text-sm font-medium tracking-wide text-content-secondary">{text}</p>
      )}
    </>
  );

  if (fullPage) {
    return (
      <div className="fixed inset-x-0 bottom-0 top-[var(--navbar-height)] z-40 flex items-center justify-center backdrop-blur-md">
        <div className="flex flex-col items-center">{spinner}</div>
      </div>
    );
  }

  if (inline) {
    return <div className={`inline-flex items-center gap-2 ${className}`}>{spinner}</div>;
  }

  return (
    <div className={`flex flex-col items-center justify-center p-6 ${className}`}>{spinner}</div>
  );
};
