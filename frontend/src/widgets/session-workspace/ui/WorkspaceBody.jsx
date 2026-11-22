import { useEffect, useRef, useState } from 'react';
import { ArrowLeftIcon, ClipboardDocumentListIcon } from '@heroicons/react/24/outline';
import { RegenerateModal, useAnswerReview } from '@/features/answer-review';
import { SynthesisTab } from '@/features/summaries';
import { useAnswerChanges } from '@/shared/lib/answer-sync';
import { Button, EmptyState } from '@/shared/ui';
import { useQuestionFilters } from '../model/useQuestionFilters';
import { useQuestionnaireReview } from '../model/useQuestionnaireReview';
import { DocumentsCard } from './DocumentsCard';
import { FundCard } from './FundCard';
import { QuestionDetail } from './QuestionDetail';
import { QuestionList } from './QuestionList';
import { QuestionnaireList } from './QuestionnaireList';
import { SectionNav } from './SectionNav';

// One row on a wide screen: the side columns keep their width and stay in
// view (each scrolls on its own); the list takes the rest. Narrower, the row
// wraps: the details go under the list, then everything stacks, each column
// at full width. 1320px: the three columns, their gaps and the page margins.
const WIDE = 'min-[1320px]:sticky min-[1320px]:top-[calc(var(--navbar-height)_+_1rem)]';
const WIDE_SCROLL =
  'min-[1320px]:max-h-[calc(100dvh_-_var(--navbar-height)_-_2rem)] min-[1320px]:overflow-y-auto';
const LEFT = `flex min-w-0 flex-[1_1_260px] flex-col gap-3 min-[1320px]:flex-[0_0_272px] ${WIDE} ${WIDE_SCROLL}`;
const CENTRE = 'min-w-0 flex-[999_1_520px]';
const RIGHT = `min-w-0 flex-[1_1_380px] min-[1320px]:flex-[0_0_400px] min-[1600px]:flex-[0_0_440px] ${WIDE} ${WIDE_SCROLL}`;

const scrollBehavior = () =>
  window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';

// The columns stack on a narrow screen: what was picked may sit far below.
const revealIfFar = getElement =>
  requestAnimationFrame(() => {
    const element = getElement();
    if (element && element.getBoundingClientRect().top > window.innerHeight * 0.75) {
      element.scrollIntoView({ behavior: scrollBehavior(), block: 'start' });
    }
  });

// Why the documents of the questionnaire cannot be changed now, if they cannot.
const lockReasonOf = (ddType, runs) => {
  if (runs.canStart(ddType)) return null;
  if (runs.isRunning) return 'The documents cannot be changed while a questionnaire is running.';
  if (ddType.is_active === false)
    return 'This questionnaire is deactivated: its documents stay as they are.';
  return 'The run is finished: its documents stay as they are.';
};

/**
 * The three columns of the workspace for one questionnaire: the due diligence
 * and its questionnaires on the left, the questions (or the synthesis) in the
 * centre, the selected question on the right. Mounted once per questionnaire:
 * changing it starts from a clean list.
 */
export const WorkspaceBody = ({
  session,
  sessionId,
  ddTypes,
  ddType,
  progressByCode,
  runs,
  stores,
  structures,
  tab,
  onTabChange,
  onSelectDdType,
}) => {
  const code = ddType?.code;
  const progress = code ? progressByCode[code] : undefined;
  const review = useQuestionnaireReview({
    sessionId,
    ddTypeCode: code,
    structure: structures.of(code),
    structureReady: structures.ready,
    // Each answer the run adds moves the progress: the list follows it.
    liveKey: progress ? `${progress.status}:${progress.questions_completed}` : '',
  });
  const filters = useQuestionFilters(review.rows);
  const answerReview = useAnswerReview({
    sessionId: session.id,
    onChange: review.patchAnswer,
    setStatus: review.setStatus,
    reload: review.reload,
    onDocumentAdded: stores.load,
  });

  // An answer of this due diligence changed in another window (its own answer
  // window, most often): the list follows, behind the page, and so do the
  // versions shown for it.
  useAnswerChanges(change => {
    if (String(change.sessionId) !== String(session.id)) return;
    review.reload({ silent: true });
    const { history } = answerReview;
    if (history.versionHistory[change.answerId]) history.fetchVersionHistory(change.answerId);
  });

  const [selectedKey, setSelectedKey] = useState(null);
  const listRef = useRef(null);
  const detailRef = useRef(null);

  // Once the questions are known, one is open: the first to review, else the
  // first. A selection that is no longer listed falls back the same way.
  useEffect(() => {
    if (review.loading) return;
    if (selectedKey && review.rows.some(row => row.key === selectedKey)) return;
    const first = review.rows.find(row => row.state === 'review') || review.rows[0];
    setSelectedKey(first ? first.key : null);
  }, [review.loading, review.rows, selectedKey]);

  const selectedRow = review.rows.find(row => row.key === selectedKey) || null;

  const selectQuestion = (key, { reveal = false } = {}) => {
    setSelectedKey(key);
    if (reveal) revealIfFar(() => detailRef.current);
  };

  const selectSection = key => {
    filters.setSection(key);
    if (tab !== 'questions') onTabChange('questions');
    revealIfFar(() => listRef.current);
  };

  const backToList = () => {
    const rowButton =
      selectedKey && listRef.current?.querySelector(`[data-row-key="${CSS.escape(selectedKey)}"]`);
    (rowButton || listRef.current)?.scrollIntoView({ behavior: scrollBehavior(), block: 'center' });
    rowButton?.focus({ preventScroll: true });
  };

  const sectionLabel =
    review.sections.find(section => section.key === filters.section)?.label || 'All questions';

  let centre;
  if (!ddType) {
    centre = (
      <EmptyState
        icon={ClipboardDocumentListIcon}
        title="No questionnaire"
        text="This due diligence has no questionnaire to answer."
        className="rounded-xl border border-border bg-surface"
      />
    );
  } else if (tab === 'synthesis') {
    centre = (
      <section aria-label="Synthesis" className="rounded-xl border border-border bg-surface">
        <div className="border-b border-border px-2 py-2">
          <Button variant="ghost" icon={ArrowLeftIcon} onClick={() => onTabChange('questions')}>
            Back to the questions
          </Button>
        </div>
        <div className="p-4 sm:p-5">
          <SynthesisTab sessionId={sessionId} ddTypeCode={code} ddTypeName={ddType.name} />
        </div>
      </section>
    );
  } else {
    centre = (
      <QuestionList
        ref={listRef}
        review={review}
        filters={filters}
        sectionLabel={sectionLabel}
        selectedKey={selectedKey}
        onSelect={selectQuestion}
      />
    );
  }

  return (
    <>
      <div className="flex flex-wrap items-start gap-5">
        <div className={LEFT}>
          <FundCard session={session} />
          {ddType && (
            <DocumentsCard
              ddType={ddType}
              ddTypeCodes={ddTypes.map(item => item.code)}
              stores={stores}
              lockReason={lockReasonOf(ddType, runs)}
              progress={progress}
            />
          )}
          {ddTypes.length > 0 && (
            <QuestionnaireList
              ddTypes={ddTypes}
              selectedCode={code}
              onSelect={onSelectDdType}
              progressByCode={progressByCode}
              questionCounts={structures.counts}
            />
          )}
          {ddType && review.sections.length > 0 && (
            <SectionNav
              sections={review.sections}
              done={review.done}
              total={review.total}
              selected={filters.section}
              onSelect={selectSection}
            />
          )}
        </div>

        <div className={CENTRE}>{centre}</div>

        {ddType && (
          <QuestionDetail
            ref={detailRef}
            row={selectedRow}
            review={answerReview}
            sessionId={sessionId}
            runStatus={progress?.status || 'not_started'}
            onBackToList={backToList}
            className={RIGHT}
          />
        )}
      </div>

      <RegenerateModal
        isOpen={answerReview.regeneration.targetId !== null}
        onClose={answerReview.regeneration.close}
        onSubmit={answerReview.regeneration.submit}
        loading={answerReview.regeneration.regeneratingId !== null}
      />
    </>
  );
};
