import { SECONDS_PER_QUESTION, TOKENS_PER_QUESTION, estimateRun } from '../lib/questionnaires';
import { joinNames, plural } from '../lib/text';

const Muted = ({ children }) => <span className="text-content-muted">{children}</span>;

const Tile = ({ label, value }) => (
  <div className="form-surface flex-[1_1_10rem] px-4 py-3.5">
    <p className="text-xs text-content-muted">{label}</p>
    <p className="mt-0.5 text-xl font-semibold tracking-tight text-content tabular-nums">{value}</p>
  </div>
);

/**
 * Step 4: everything chosen, each part with its way back, and what the run
 * should cost. `fields`: the fund as the AI reads it. `collection`:
 * { name, files } or null. `questions`: their count, null when unknown.
 * `onEdit(step)`.
 */
export const ReviewStep = ({ fields: draft, details, collection, chosen, questions, onEdit }) => {
  // As they will be stored: trimmed.
  const fields = Object.fromEntries(
    Object.entries(draft).map(([key, value]) => [key, (value || '').trim()])
  );
  const site = url => url && <span className="text-content-secondary"> · {url}</span>;
  const rows = [
    {
      label: 'Fund',
      step: 1,
      value: (
        <>
          {fields.name || <Muted>Not named</Muted>}
          {site(fields.website_url)}
        </>
      ),
    },
    {
      label: 'Management company',
      step: 1,
      value: fields.management_company_name ? (
        <>
          {fields.management_company_name}
          {site(fields.management_company_website)}
        </>
      ) : (
        <Muted>Not set</Muted>
      ),
    },
    {
      label: 'Short description',
      step: 1,
      value: fields.description ? (
        <span className="whitespace-pre-line">{fields.description}</span>
      ) : (
        <Muted>None</Muted>
      ),
    },
    {
      label: 'Due diligence',
      step: 1,
      value: (
        <>
          {details.name.trim() || <Muted>Not named</Muted>}
          {details.description.trim() && (
            <span className="block text-content-secondary whitespace-pre-line">
              {details.description.trim()}
            </span>
          )}
        </>
      ),
    },
    {
      label: 'Documents',
      step: 2,
      value: collection ? (
        <>
          {collection.name}
          {collection.files !== null && (
            <span className="text-content-secondary"> · {plural(collection.files, 'file')}</span>
          )}
        </>
      ) : (
        <Muted>None: the AI searches the web only</Muted>
      ),
    },
    {
      label: chosen.length === 1 ? 'Questionnaire' : 'Questionnaires',
      step: 3,
      value: chosen.length ? (
        <>
          {joinNames(chosen.map(questionnaire => questionnaire.name))}
          {questions !== null && (
            <span className="text-content-secondary"> · {plural(questions, 'question')}</span>
          )}
        </>
      ) : (
        <Muted>None chosen</Muted>
      ),
    },
  ];
  const estimate = estimateRun(questions);

  return (
    <div className="flex flex-col gap-5">
      <dl className="overflow-hidden rounded-xl border border-border">
        {rows.map(row => (
          <div
            key={row.label}
            className="flex flex-wrap items-start gap-x-4 gap-y-1 border-b border-border px-4 py-3 last:border-b-0"
          >
            <dt className="w-36 shrink-0 pt-0.5 text-[0.8125rem] text-content-muted">
              {row.label}
            </dt>
            <dd className="flex min-w-0 flex-[1_1_15rem] items-start justify-between gap-3">
              <span className="min-w-0 pt-0.5 text-sm text-content break-words">{row.value}</span>
              <button
                type="button"
                onClick={() => onEdit(row.step)}
                className="-my-2 min-h-10 shrink-0 px-2 text-[0.8125rem] text-link"
                aria-label={`Edit: ${row.label}`}
              >
                Edit
              </button>
            </dd>
          </div>
        ))}
      </dl>

      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap gap-3">
          <Tile label="Questions" value={estimate.questions} />
          <Tile label="Time, about" value={estimate.time} />
          <Tile label="Tokens sent, about" value={estimate.tokens} />
        </div>
        <p className="text-xs text-content-muted">
          About {SECONDS_PER_QUESTION} seconds and {TOKENS_PER_QUESTION.toLocaleString('en-US')}{' '}
          tokens per question: OpenAI&apos;s load and the length of the passages found move both.
        </p>
      </div>

      <p className="text-[0.8125rem] text-content-secondary">
        You start the run on the due diligence&apos;s page, and can pause it at any time: the
        answers written so far stay, and paused time is not counted.
      </p>
    </div>
  );
};
