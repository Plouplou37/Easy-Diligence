import { Fragment } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  PencilSquareIcon,
} from '@heroicons/react/24/outline';
import { getDdTypeIcon } from '@/entities/dd-type';
import { formatRelative } from '@/shared/lib/format';
import { getToneStyles } from '@/shared/lib/status';
import { Badge, Button, StatusBadge, tableStyles } from '@/shared/ui';

// A run whose last answer is older than this has probably stopped (server
// restarted mid-run): the execution stays `in_progress` with nothing behind it.
const STALLED_AFTER_MS = 10 * 60 * 1000;

const Progress = ({ percentage }) => {
  let tone = 'neutral';
  if (percentage >= 100) tone = 'success';
  else if (percentage > 0) tone = 'info';
  return (
    <div className="flex-1 h-1.5 rounded-full bg-surface-hover overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-300 ${getToneStyles(tone).fill}`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
};

const DdTypeRow = ({ ddType, onOpenSession, onOpenAnswers }) => {
  const Icon = getDdTypeIcon(ddType);
  const started = ddType.status !== 'not_started';
  const stalled =
    ddType.status === 'in_progress' &&
    ddType.last_answer_at &&
    Date.now() - new Date(ddType.last_answer_at).getTime() > STALLED_AFTER_MS;

  return (
    <tr className="bg-surface-bg">
      <td className={`${tableStyles.td} pl-8`}>
        <span className="flex items-center gap-2 min-w-0">
          <Icon className="w-4 h-4 shrink-0 text-content-muted" />
          <span className="truncate text-content-secondary" title={ddType.name}>
            {ddType.name}
          </span>
          {ddType.is_active === false && (
            <Badge variant="warning" size="sm">
              Inactive
            </Badge>
          )}
        </span>
      </td>
      <td className={tableStyles.td}>
        <span className="flex flex-wrap items-center gap-2">
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
            <Badge variant="success" size="sm" icon={CheckCircleIcon}>
              Synthesis
            </Badge>
          )}
        </span>
      </td>
      <td className={tableStyles.td}>
        <span className="flex items-center gap-1.5">
          <StatusBadge status={ddType.status} size="sm" />
          {stalled && (
            <span
              title={`No new answer since ${new Date(ddType.last_answer_at).toLocaleString()}: the run may have stopped. Open the session to resume it.`}
            >
              <ExclamationTriangleIcon className="w-4 h-4 text-theme-warning" />
            </span>
          )}
        </span>
      </td>
      <td className={`${tableStyles.td} whitespace-nowrap`}>
        {started ? (
          <span className="flex items-center gap-1">
            <Button size="sm" variant="secondary" onClick={() => onOpenAnswers(ddType)}>
              Answers
            </Button>
            {ddType.has_synthesis && (
              <Button size="sm" variant="ghost" onClick={() => onOpenAnswers(ddType, 'synthesis')}>
                Synthesis
              </Button>
            )}
          </span>
        ) : (
          <Button size="sm" variant="ghost" onClick={onOpenSession}>
            Open
          </Button>
        )}
      </td>
      <td className={tableStyles.td}>
        <div className="flex items-center gap-2">
          <Progress percentage={ddType.percentage} />
          <span className="w-14 text-right text-xs text-content-secondary tabular-nums">
            {ddType.answered}/{ddType.total_questions}
          </span>
        </div>
      </td>
    </tr>
  );
};

/** The sessions, one sub-row per DD type. `showOwner`: an admin sees whose session it is. */
export const SessionsTable = ({ sessions, showOwner }) => {
  const navigate = useNavigate();
  const sessionUrl = session => `/session/${session.session_code || session.id}`;

  return (
    <div className={tableStyles.wrapper}>
      <table className={`${tableStyles.table} ${tableStyles.inPanel}`}>
        <thead className={tableStyles.thead}>
          <tr>
            <th className={tableStyles.th}>Session</th>
            <th className={tableStyles.th}>Fund / Management Company</th>
            <th className={tableStyles.th}>Status</th>
            <th className={tableStyles.th}>Last Activity</th>
            <th className={`${tableStyles.th} w-48`}>Progress</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map(session => {
            const openSession = () => navigate(sessionUrl(session));
            const openAnswers = (ddType, tab) =>
              navigate(
                `${sessionUrl(session)}/answers?dd_type=${ddType.code}${tab ? `&tab=${tab}` : ''}`
              );
            return (
              <Fragment key={session.id}>
                <tr onClick={openSession} className={`${tableStyles.row} cursor-pointer`}>
                  <td className={tableStyles.td}>
                    <span
                      className="block max-w-md text-sm font-medium text-content truncate"
                      title={session.description || session.name}
                    >
                      {session.name}
                    </span>
                    {showOwner && session.created_by_username && (
                      <span className="text-xs text-content-muted">
                        {session.created_by_username}
                      </span>
                    )}
                  </td>
                  <td className={`${tableStyles.td} text-sm`}>
                    <span className="block">{session.company_name}</span>
                    {session.management_company_name && (
                      <span className="block text-xs text-content-secondary">
                        {session.management_company_name}
                      </span>
                    )}
                  </td>
                  <td className={tableStyles.td}>
                    <StatusBadge status={session.status} />
                  </td>
                  <td
                    className={`${tableStyles.td} whitespace-nowrap text-content-secondary tabular-nums`}
                    title={`Created ${new Date(session.created_at).toLocaleDateString()}`}
                  >
                    {formatRelative(session.last_activity_at)}
                  </td>
                  <td className={tableStyles.td}>
                    <div className="flex items-center gap-2">
                      <Progress percentage={session.progress} />
                      <span className="w-9 text-right text-xs font-medium text-content tabular-nums">
                        {session.progress}%
                      </span>
                    </div>
                  </td>
                </tr>
                {session.dd_types.map(ddType => (
                  <DdTypeRow
                    key={`${session.id}-${ddType.dd_type_id}`}
                    ddType={ddType}
                    onOpenSession={openSession}
                    onOpenAnswers={openAnswers}
                  />
                ))}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
