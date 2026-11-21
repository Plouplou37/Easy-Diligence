/** Marks a field the model never reads (the opposite of shared/ui's AiBadge). */
export const NotSentNote = ({ children = 'Not sent — for your team' }) => (
  <span className="text-[0.6875rem] font-semibold leading-4 text-content-muted whitespace-nowrap">
    {children}
  </span>
);
