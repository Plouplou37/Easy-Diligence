import { useId } from 'react';
import { CheckCircleIcon, LockClosedIcon } from '@heroicons/react/24/outline';
import { Badge, field, panel } from '@/shared/ui';

const Figure = ({ label, children }) => (
  <div className="form-surface min-w-24 px-4 py-2.5">
    <dt className="text-xs text-content-muted">{label}</dt>
    <dd className="mt-0.5 text-lg font-semibold tabular-nums text-content">{children}</dd>
  </div>
);

/** The questionnaire shown on the page, its size and its status. */
const DDTypeSelector = ({ ddTypes, selectedCode, onChange, selectedDdType }) => {
  const selectId = useId();
  const sections = selectedDdType?.sections || [];
  const questions = sections.reduce((sum, section) => sum + (section.questions?.length || 0), 0);
  const validated = Boolean(selectedDdType?.is_validated);

  return (
    <div className={`${panel.base} p-5`}>
      <div className="flex flex-wrap items-end gap-x-6 gap-y-4">
        <div className="min-w-0 flex-[1_1_18rem]">
          <label htmlFor={selectId} className={field.label}>
            Questionnaire
          </label>
          <select
            id={selectId}
            value={selectedCode || ''}
            onChange={e => onChange(e.target.value)}
            className="form-input h-10 w-full text-sm"
          >
            <option value="">Choose a questionnaire…</option>
            {ddTypes.map(ddType => (
              <option key={ddType.code} value={ddType.code}>
                {ddType.name}
                {ddType.is_validated ? ' — validated' : ' — draft'}
                {ddType.is_active === false ? ', inactive' : ''}
              </option>
            ))}
          </select>
        </div>

        {selectedDdType && (
          <dl className="flex flex-wrap gap-3">
            <Figure label="Sections">{sections.length}</Figure>
            <Figure label="Questions">{questions}</Figure>
            <div className="form-surface min-w-24 px-4 py-2.5">
              <dt className="text-xs text-content-muted">Status</dt>
              <dd className="mt-1.5 flex flex-wrap gap-1.5">
                {validated ? (
                  <Badge variant="success" icon={CheckCircleIcon}>
                    Validated
                  </Badge>
                ) : (
                  <Badge variant="neutral">Draft</Badge>
                )}
                {selectedDdType.is_active === false && <Badge variant="warning">Inactive</Badge>}
              </dd>
            </div>
          </dl>
        )}
      </div>

      {selectedDdType && (
        <p className="mt-4 flex items-start gap-2 text-sm text-content-secondary">
          {validated ? (
            <>
              <LockClosedIcon className="mt-0.5 h-4 w-4 shrink-0 text-theme-success" />
              <span>
                Validated: its sections and questions are frozen, and can be read only. To change
                them, create a new questionnaire.
              </span>
            </>
          ) : (
            <span>
              Draft: its sections and questions can change. Validate it once it is final: they are
              then frozen, for good.
            </span>
          )}
        </p>
      )}
    </div>
  );
};

export default DDTypeSelector;
