import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  ArrowPathIcon,
  DocumentMagnifyingGlassIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { displayQuestionCode } from '@/entities/dd-type';
import { Button, EmptyState, LoadingSpinner } from '@/shared/ui';
import { useAnswerWork } from '../model/useAnswerWork';
import { useQuestionnaireOrder, useSession } from '../model/useWindowContext';
import { AnswerEditorCard } from './AnswerEditorCard';
import { QuestionHeader } from './QuestionHeader';
import { RegeneratePanel, SourcesPanel, VersionsPanel } from './SidePanels';
import { WindowHeader } from './WindowHeader';

const isPlainClick = event =>
  event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;

/** Why the draft no longer starts from the saved answer, with the way back to it. */
const OutdatedNotice = ({ reason, onReload }) => (
  <div role="status" className="alert alert-warning flex flex-wrap items-center gap-3">
    <ExclamationTriangleIcon className="h-5 w-5 shrink-0" />
    <p className="min-w-0 flex-[1_1_280px] text-sm">
      {reason === 'regenerated'
        ? 'The new answer is ready, and your unsaved changes are kept.'
        : 'This answer changed in another window.'}{' '}
      <span className="text-content-secondary">
        Reload to see it: your unsaved changes will be lost.
      </span>
    </p>
    <Button variant="secondary" icon={ArrowPathIcon} onClick={onReload}>
      Reload
    </Button>
  </div>
);

/**
 * One answer in a window of its own (`answerId`, of the session `sessionId`
 * of the address): the question, a wide editor with its preview, and on the
 * side its sources, a regeneration and its versions. `session` (null until
 * known) and `order` (useQuestionnaireOrder) come from the page, which keeps
 * them from one answer to the next. Mounted once per answer.
 */
const AnswerWindow = ({ sessionId, answerId, session, order, onLoaded }) => {
  const navigate = useNavigate();
  const work = useAnswerWork({ answerId, onLoaded });
  const { answer } = work;
  const [view, setView] = useState('edit');

  const ddName = session?.name || session?.company_name || answer?.session_name || 'Due diligence';
  const fund =
    session?.company_name && session.company_name !== ddName ? session.company_name : null;
  const ddTypeCode = answer?.dd_type_code || '';
  const questionnaire = order.ddType?.name || ddTypeCode || null;
  const ddUrl = `/session/${sessionId}${ddTypeCode ? `?dd_type=${encodeURIComponent(ddTypeCode)}` : ''}`;
  // An answer of another session than the address says is not this window's.
  const elsewhere = Boolean(answer && session && answer.session_id !== session.id);

  const title = answer
    ? `${displayQuestionCode(answer.question_code) || 'Answer'} — ${ddName}`
    : null;
  useEffect(() => {
    if (!title) return undefined;
    const previous = document.title;
    document.title = title;
    return () => {
      document.title = previous;
    };
  }, [title]);

  const index = answer ? order.ids.indexOf(answer.id) : -1;
  const previousId = index > 0 ? order.ids[index - 1] : null;
  const nextId = index >= 0 && index < order.ids.length - 1 ? order.ids[index + 1] : null;

  // In the same window, replacing the address: the browser's Back would
  // leave an edit without asking.
  const goTo = async id => {
    if (await work.confirmLeave())
      navigate(`/session/${sessionId}/answer/${id}`, { replace: true });
  };

  const openDueDiligence = async event => {
    if (!work.holding || !isPlainClick(event)) return;
    event.preventDefault();
    if (await work.confirmLeave()) navigate(ddUrl);
  };

  let body;
  if (work.failed || elsewhere) {
    body = (
      <EmptyState
        icon={DocumentMagnifyingGlassIcon}
        title="Answer not found"
        text="It may have been removed, or you do not have access to it."
        action={
          <Link to={ddUrl} className="text-link inline-flex min-h-10 items-center text-sm">
            Open the due diligence
          </Link>
        }
        className="rounded-xl border border-border bg-surface"
      />
    );
  } else if (!answer) {
    body = <LoadingSpinner text="Loading the answer…" className="py-16" />;
  } else {
    body = (
      <>
        <QuestionHeader
          answer={answer}
          position={index + 1}
          total={order.ids.length}
          onPrevious={previousId ? () => goTo(previousId) : undefined}
          onNext={nextId ? () => goTo(nextId) : undefined}
        />

        {answer.status === 'failed' && (
          <p className="alert alert-error">
            The AI could not answer this question. Regenerate it here, or resume the run from the
            due diligence.
          </p>
        )}
        {work.outdated && <OutdatedNotice reason={work.outdated} onReload={work.reload} />}

        {/* Side by side on a wide window; narrower, the side goes under. */}
        <div className="flex flex-wrap items-start gap-5">
          <div className="min-w-0 flex-[999_1_640px]">
            <AnswerEditorCard work={work} view={view} onViewChange={setView} />
          </div>
          <aside
            aria-label="Sources, regeneration and versions"
            className="flex min-w-0 flex-[1_1_360px] flex-col gap-5"
          >
            <SourcesPanel draft={work.draft} />
            <RegeneratePanel regenerating={work.regenerating} onRegenerate={work.regenerate} />
            <VersionsPanel
              answer={answer}
              versions={work.history.versionHistory[answer.id]}
              onRevert={work.revert}
            />
          </aside>
        </div>
      </>
    );
  }

  return (
    <div className="min-h-screen bg-surface-bg">
      <WindowHeader
        ddName={ddName}
        fund={fund}
        questionnaire={questionnaire}
        ddUrl={ddUrl}
        onOpenDueDiligence={openDueDiligence}
      />
      <main className="space-y-5 px-4 py-5 sm:px-6 lg:px-8">{body}</main>
    </div>
  );
};

/**
 * An answer of a due diligence in a window of its own (opened from the
 * workspace), outside the application's layout. The due diligence and the
 * order of its questionnaire stay loaded from one answer to the next.
 */
const AnswerWindowPage = () => {
  const { sessionId, answerId } = useParams();
  const session = useSession(sessionId);
  const [ddTypeCode, setDdTypeCode] = useState(null);
  const order = useQuestionnaireOrder(sessionId, ddTypeCode);
  const onLoaded = useCallback(answer => setDdTypeCode(answer.dd_type_code || null), []);

  return (
    <AnswerWindow
      key={answerId}
      sessionId={sessionId}
      answerId={answerId}
      session={session}
      order={order}
      onLoaded={onLoaded}
    />
  );
};

export default AnswerWindowPage;
