import {
  ArrowPathRoundedSquareIcon,
  ClockIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { Button, EmptyState, LoadingSpinner } from '@/shared/ui';
import { useSynthesis } from '../model/useSynthesis';
import SummaryBlock from './SummaryBlock';

// OpenAI's raw statuses read as jargon on screen ("in_progress").
const BATCH_STATUS_LABELS = {
  validating: 'being validated',
  in_progress: 'in progress',
  finalizing: 'being finalized',
};

const isGlobal = summary => summary.section_id === null || summary.section_id === undefined;

/** Where the OpenAI batch stands, and its cancellation while it runs. */
const BatchBanner = ({ batch, pending, cancelling, onCancel }) => {
  let tone = 'alert-error';
  if (pending) tone = 'alert-info';
  else if (batch.status === 'collected') tone = 'alert-success';

  let text;
  if (batch.status === 'cancelling') {
    text = 'Cancelling… The buttons come back once OpenAI confirms it.';
  } else if (pending) {
    // No count before OpenAI has one: validation used to show "0/0".
    const count =
      batch.total > 0 ? ` — ${batch.completed ?? 0}/${batch.total} section summaries` : '';
    text =
      `Batch ${BATCH_STATUS_LABELS[batch.status] || batch.status}${count}. The result can take ` +
      'up to 24 h; this page updates itself, and nothing is lost if you leave it.';
  } else if (batch.status === 'cancelled') {
    text = 'Batch cancelled: no summary was produced. You can generate the synthesis again.';
  } else if (batch.status === 'collected') {
    const sections = typeof batch.sections === 'number' ? ` (${batch.sections} sections)` : '';
    text = `Section summaries produced by batch${sections}, synthesis generated.`;
  } else {
    text = `Batch ended without a result (${batch.status})${batch.message ? ` — ${batch.message}` : ''}.`;
  }

  return (
    <div className={`alert flex flex-wrap items-start justify-between gap-3 ${tone}`}>
      <div className="min-w-0 flex-1">{text}</div>
      {/* Hidden once cancelling: a second request would only be refused. */}
      {pending && batch.status !== 'cancelling' && (
        <Button onClick={onCancel} variant="danger" disabled={cancelling}>
          {cancelling ? 'Cancelling…' : 'Cancel the batch'}
        </Button>
      )}
    </div>
  );
};

/** The synthesis of one questionnaire: per-section summaries and a global one. */
const SynthesisTab = ({ sessionId, ddTypeCode, ddTypeName }) => {
  const synthesis = useSynthesis(sessionId, ddTypeCode);
  const { summaries, batch, batchPending, generating } = synthesis;

  // The synthesis is strictly per questionnaire.
  if (!ddTypeCode) {
    return (
      <EmptyState
        icon={DocumentTextIcon}
        title="Select a questionnaire"
        text="The synthesis is written per questionnaire. Pick one to generate or read its synthesis."
      />
    );
  }

  const global = summaries.find(isGlobal);
  const sectionSummaries = summaries.filter(summary => !isGlobal(summary));

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1 basis-64">
          <h2 className="text-base font-semibold text-content">
            Synthesis of {ddTypeName || ddTypeCode}
          </h2>
          <p className="mt-1 text-sm text-content-secondary">
            A summary per section and an overall synthesis (both in the PDF report), written from
            the current answers.
          </p>
        </div>
        {/* While OpenAI still holds the job, neither path may be relaunched: the
            backend refuses a second submission, and a synchronous run would be
            overwritten by the batch landing behind it. */}
        <div className="flex flex-wrap items-center gap-2">
          <Button
            onClick={synthesis.generate}
            variant="primary"
            icon={ArrowPathRoundedSquareIcon}
            disabled={generating || batchPending}
          >
            {generating
              ? 'Generating…'
              : summaries.length > 0
                ? 'Regenerate the synthesis'
                : 'Generate the synthesis'}
          </Button>
          {/* Same result at half price, but OpenAI has up to 24h to deliver it.
              Secondary on purpose: the immediate path stays the obvious one. */}
          <Button
            onClick={synthesis.generateBatch}
            variant="secondary"
            icon={ClockIcon}
            disabled={generating || batchPending}
            title="Goes through OpenAI's Batch API: half the price, but the result can take up to 24 h."
          >
            Generate by batch (−50%)
          </Button>
        </div>
      </div>

      {batch && (
        <BatchBanner
          batch={batch}
          pending={batchPending}
          cancelling={synthesis.cancellingBatch}
          onCancel={synthesis.cancelBatch}
        />
      )}

      {synthesis.loading ? (
        <LoadingSpinner text="Loading the synthesis…" />
      ) : summaries.length === 0 ? (
        <EmptyState
          icon={DocumentTextIcon}
          title="No synthesis yet"
          text="“Generate the synthesis” writes it from the current answers."
          className="rounded-lg border border-dashed border-border-hover"
        />
      ) : (
        <>
          {global && (
            <SummaryBlock title="Overall synthesis" summary={global} onSaved={synthesis.load} />
          )}
          {sectionSummaries.length > 0 && (
            <div className="space-y-3">
              <h3 className="eyebrow">Section summaries</h3>
              {sectionSummaries.map(summary => (
                <SummaryBlock
                  key={summary.id}
                  title={summary.section_title || 'Section'}
                  summary={summary}
                  onSaved={synthesis.load}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default SynthesisTab;
