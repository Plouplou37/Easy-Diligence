import { Link } from 'react-router-dom';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  PencilSquareIcon,
  UserCircleIcon,
} from '@heroicons/react/24/outline';
import { getDdTypeIcon } from '@/entities/dd-type';
import { formatRelative } from '@/shared/lib/format';
import { getStatusLabel, getStatusStyles, getToneStyles } from '@/shared/lib/status';
import { Badge } from '@/shared/ui';
import { answeredOf, answersUrl, sessionUrl } from '../lib/sessionRow';

const FOCUS_RING =
  'focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent-blue/60';

// The links inside a row sit above the row's own link (the phone card is one
// big link): `relative`. On a phone they are 40 px tall, for a finger.
const INNER_LINK = `relative ${FOCUS_RING}`;

/**
 * The name of the due diligence, its fund and management company, and (for an
 * admin) who created it. `stretched`: the name's link covers the whole card.
 */
export const SessionTitle = ({ session, showOwner, stretched = false }) => (
  <div className="min-w-0 max-w-[24rem] lg:min-w-[13rem]">
    <Link
      to={sessionUrl(session)}
      title={session.description || session.name}
      className={`block break-words font-medium text-content ${
        stretched
          ? 'after:absolute after:inset-0 focus-visible:outline-hidden focus-visible:after:ring-2 focus-visible:after:ring-inset focus-visible:after:ring-accent-blue/60'
          : `rounded-sm hover:text-accent-blue ${FOCUS_RING}`
      }`}
    >
      {session.name}
    </Link>
    {(session.company_name || session.management_company_name) && (
      <p className="mt-0.5 text-sm text-content-secondary break-words">
        {session.company_name}
        {session.company_name && session.management_company_name && (
          <span className="text-content-muted"> · </span>
        )}
        {session.management_company_name}
      </p>
    )}
    {showOwner && session.created_by_username && (
      <p
        className="mt-1 flex items-center gap-1 text-xs text-content-muted"
        title={`Created by ${session.created_by_username}`}
      >
        <UserCircleIcon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        {session.created_by_username}
      </p>
    )}
  </div>
);

/** A thin bar and "N of M": the questions answered. */
export const QuestionsProgress = ({ answered, total }) => {
  if (!total) return <span className="text-xs text-content-muted">No questions</span>;
  const percentage = Math.min(Math.round((100 * answered) / total), 100);
  let tone = 'neutral';
  if (percentage >= 100) tone = 'success';
  else if (percentage > 0) tone = 'info';
  return (
    <div
      className="flex min-h-5 items-center gap-2.5"
      title={`${answered} of ${total} questions answered`}
    >
      <div
        role="progressbar"
        aria-label="Questions answered"
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={answered}
        className="h-1.5 min-w-16 flex-1 overflow-hidden rounded-full bg-border"
      >
        <div
          className={`h-full rounded-full transition-[width] duration-300 ${getToneStyles(tone).fill}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {/* A fixed minimum width: the bars of the rows line up, whatever their counts. */}
      <span className="min-w-16 shrink-0 whitespace-nowrap text-right text-xs text-content-secondary tabular-nums">
        {answered} of {total}
      </span>
    </div>
  );
};

/** A run that looks stopped: in progress, but no new answer for a while. */
export const StalledNote = ({ runs }) => {
  if (!runs.length) return null;
  const [first] = runs;
  const detail = runs
    .map(run => `${run.name}: no new answer since ${new Date(run.last_answer_at).toLocaleString()}`)
    .join('\n');
  return (
    <div
      className="mt-1.5 text-xs"
      title={`${detail}\nThe run may have stopped. Open the due diligence to resume it.`}
    >
      <p className="flex items-center gap-1 font-medium text-theme-warning">
        <ExclamationTriangleIcon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        May have stopped
      </p>
      <p className="mt-0.5 text-content-muted whitespace-nowrap">
        Last answer {formatRelative(first.last_answer_at)}
      </p>
    </div>
  );
};

/**
 * One questionnaire of the due diligence: its name (a link to its answers once
 * started), its own status when it differs from the due diligence's, its count
 * when there are several, and what calls for attention.
 */
const QuestionnaireLine = ({ session, ddType, several }) => {
  const Icon = getDdTypeIcon(ddType);
  const started = ddType.status !== 'not_started';
  const ownStatus = ddType.status !== session.status;

  return (
    <li className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
      <span className="flex min-w-0 max-w-full items-center gap-2">
        <Icon className="h-4 w-4 shrink-0 text-content-muted" aria-hidden="true" />
        {started ? (
          <Link
            to={answersUrl(session, ddType)}
            title={`Open the answers to ${ddType.name}`}
            className={`${INNER_LINK} block max-w-[16rem] truncate rounded-sm py-2.5 text-sm text-content hover:text-accent-blue hover:underline underline-offset-2 lg:max-w-[14rem] lg:py-0`}
          >
            {ddType.name}
          </Link>
        ) : (
          <span
            className="block max-w-[16rem] truncate py-2.5 text-sm text-content-secondary lg:max-w-[14rem] lg:py-0"
            title={ddType.name}
          >
            {ddType.name}
          </span>
        )}
      </span>
      {ownStatus && (
        <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-xs text-content-secondary">
          <span
            className={`h-1.5 w-1.5 rounded-full ${getStatusStyles(ddType.status).dot}`}
            aria-hidden="true"
          />
          {getStatusLabel(ddType.status)}
        </span>
      )}
      {several && ddType.total_questions > 0 && (
        <span className="whitespace-nowrap text-xs text-content-muted tabular-nums">
          {answeredOf(ddType)} of {ddType.total_questions}
        </span>
      )}
      {ddType.is_active === false && (
        <Badge variant="warning" size="sm">
          Inactive
        </Badge>
      )}
      {ddType.to_review > 0 && (
        <Badge variant="warning" size="sm" icon={PencilSquareIcon}>
          {ddType.to_review} to review
        </Badge>
      )}
      {ddType.failed > 0 && (
        <Badge variant="error" size="sm">
          {ddType.failed} failed
        </Badge>
      )}
      {ddType.has_synthesis && (
        <Link
          to={answersUrl(session, ddType, 'synthesis')}
          title={`Open the synthesis of ${ddType.name}`}
          className={`${INNER_LINK} inline-flex min-h-10 items-center rounded-full transition-opacity hover:opacity-80 lg:min-h-0`}
        >
          <Badge variant="success" size="sm" icon={CheckCircleIcon}>
            Synthesis
          </Badge>
        </Link>
      )}
    </li>
  );
};

/** The questionnaires of a due diligence, one line each. */
export const QuestionnaireList = ({ session }) => {
  if (!session.dd_types.length) {
    return <span className="text-sm text-content-muted">No questionnaire</span>;
  }
  const several = session.dd_types.length > 1;
  return (
    <ul className="flex flex-col gap-1 lg:gap-1.5">
      {session.dd_types.map(ddType => (
        <QuestionnaireLine
          key={ddType.dd_type_id}
          session={session}
          ddType={ddType}
          several={several}
        />
      ))}
    </ul>
  );
};
