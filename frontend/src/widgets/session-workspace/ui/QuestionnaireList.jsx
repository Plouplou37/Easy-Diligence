import { getDdTypeIcon } from '@/entities/dd-type';
import { getStatusStyles } from '@/shared/lib/status';
import { Badge, StatusBadge } from '@/shared/ui';
import { FOCUS_RING } from '../lib/focus';
import { ThinBar } from './Chips';

/**
 * The questionnaires of the due diligence, each with its run's status and
 * progress: picking one shows it in the rest of the page.
 */
export const QuestionnaireList = ({
  ddTypes,
  selectedCode,
  onSelect,
  progressByCode,
  questionCounts,
}) => (
  <section
    aria-labelledby="questionnaires-title"
    className="rounded-xl border border-border bg-surface p-3"
  >
    <h2 id="questionnaires-title" className="eyebrow px-1 pb-2">
      {ddTypes.length === 1 ? 'Questionnaire' : `Questionnaires (${ddTypes.length})`}
    </h2>
    <ul className="space-y-1">
      {ddTypes.map(ddType => {
        const progress = progressByCode[ddType.code];
        const status = progress?.status || 'not_started';
        const done = progress?.questions_completed || 0;
        const total = progress?.total_questions || questionCounts[ddType.code] || 0;
        const selected = ddType.code === selectedCode;
        // Outline icon guessed from the name: the stored `icon` is an emoji.
        const Icon = getDdTypeIcon(ddType);
        return (
          <li key={ddType.code}>
            <button
              type="button"
              onClick={() => onSelect(ddType.code)}
              aria-pressed={selected}
              title={ddType.description || undefined}
              className={`w-full rounded-lg border px-2.5 py-2.5 text-left transition-colors ${FOCUS_RING} ${
                selected
                  ? 'border-primary bg-primary-dark'
                  : 'border-transparent hover:bg-surface-hover'
              }`}
            >
              <span className="flex items-start gap-2">
                <Icon className="mt-0.5 h-4 w-4 shrink-0 text-content-secondary" />
                <span className="min-w-0 flex-1 text-sm font-medium text-content wrap-break-word">
                  {ddType.name}
                </span>
              </span>
              <span className="mt-2 flex items-center justify-between gap-2">
                <span className="flex flex-wrap items-center gap-1">
                  <StatusBadge status={status} size="sm" />
                  {ddType.is_active === false && (
                    <Badge variant="warning" size="sm">
                      Inactive
                    </Badge>
                  )}
                </span>
                <span className="text-xs text-content-secondary tabular-nums">
                  {done}/{total}
                </span>
              </span>
              <ThinBar
                percentage={total > 0 ? (done / total) * 100 : 0}
                fill={getStatusStyles(status).fill}
                className="mt-2"
              />
            </button>
          </li>
        );
      })}
    </ul>
  </section>
);
