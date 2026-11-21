/**
 * The head of a step. The title takes the focus when the step opens
 * (`headingRef`), so the keyboard and screen readers start from it.
 */
export const StepHeading = ({ number, total, title, description, headingRef }) => (
  <div>
    <p className="eyebrow font-semibold">
      Step {number} of {total}
    </p>
    <h2
      id="step-title"
      ref={headingRef}
      tabIndex={-1}
      className="mt-1 text-xl font-semibold tracking-tight text-content focus:outline-hidden"
    >
      {title}
    </h2>
    {description && <p className="mt-1 text-sm text-content-secondary">{description}</p>}
  </div>
);
