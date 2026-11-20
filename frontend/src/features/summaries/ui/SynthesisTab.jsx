import {
  ArrowPathRoundedSquareIcon,
  ClockIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { Button, LoadingSpinner, emptyState, panel } from '@/shared/ui';
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
    <div className={`alert flex items-start justify-between gap-4 ${tone}`}>
      <div>{text}</div>
      {/* Hidden once cancelling: a second request would only be refused. */}
      {pending && batch.status !== 'cancelling' && (
        <Button onClick={onCancel} variant="danger" size="sm" disabled={cancelling}>
          {cancelling ? 'Cancelling…' : 'Cancel the batch'}
        </Button>
      )}
    </div>
  );
};

/** The synthesis of one DD type: per-section summaries and a global one. */
const SynthesisTab = ({ sessionId, ddTypeCode, ddTypeName }) => {
  const synthesis = useSynthesis(sessionId, ddTypeCode);
  const { summaries, batch, batchPending, generating } = synthesis;

  // The synthesis is strictly per DD type.
  if (!ddTypeCode) {
    return (
      <div className={`${panel.base} ${emptyState.wrapper}`}>
        <DocumentTextIcon className={emptyState.icon} />
        <h3 className={emptyState.title}>Select a DD type</h3>
        <p className={emptyState.text}>
          The synthesis is written per DD type. Open the review of one DD type to generate or read
          its synthesis.
        </p>
      </div>
    );
  }

  const global = summaries.find(isGlobal);
  const sectionSummaries = summaries.filter(summary => !isGlobal(summary));

  return (
    <div className="space-y-6 pb-12">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium text-content">
            Synthesis — {ddTypeName || ddTypeCode}
          </h2>
          <p className="text-sm text-content-muted">
            A summary per section and an overall synthesis (both in the PDF report), written from
            the current answers.
          </p>
        </div>
        {/* While OpenAI still holds the job, neither path may be relaunched: the
            backend refuses a second submission, and a synchronous run would be
            overwritten by the batch landing behind it. */}
        <div className="flex items-center gap-3">
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
        <div className="py-12 flex justify-center">
          <LoadingSpinner size="lg" text="Loading the synthesis…" />
        </div>
      ) : summaries.length === 0 ? (
        <div className={`${emptyState.wrapper} border-2 border-dashed border-border rounded-lg`}>
          <DocumentTextIcon className={emptyState.icon} />
          <h3 className={emptyState.title}>No synthesis yet</h3>
          <p className={emptyState.text}>
            Click “Generate the synthesis” to write it from the current answers.
          </p>
        </div>
      ) : (
        <>
          {global && (
            <SummaryBlock title="Overall synthesis" summary={global} onSaved={synthesis.load} />
          )}
          {sectionSummaries.length > 0 && (
            <div className="space-y-4">
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
