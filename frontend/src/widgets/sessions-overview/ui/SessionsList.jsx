import { useNavigate } from 'react-router-dom';
import { ChevronRightIcon } from '@heroicons/react/24/outline';
import { formatRelative } from '@/shared/lib/format';
import { StatusBadge, tableStyles } from '@/shared/ui';
import { sessionUrl, stalledRuns } from '../lib/sessionRow';
import { QuestionnaireList, QuestionsProgress, SessionTitle, StalledNote } from './SessionParts';

// Cells aligned on their first line: a due diligence with several
// questionnaires is taller than the others.
const TD = 'border-b border-border px-3 py-3.5 align-top text-content';
// The first and last columns line up with the toolbar above the table.
const EDGES =
  '[&_th:first-child]:pl-5 [&_td:first-child]:pl-5 [&_th:last-child]:pr-5 [&_td:last-child]:pr-5';

const lastActivity = session => ({
  label: formatRelative(session.last_activity_at),
  title: `Created ${new Date(session.created_at).toLocaleDateString()}`,
});

/** From the large screens up: one row per due diligence, the whole row opens it. */
const Table = ({ sessions, showOwner }) => {
  const navigate = useNavigate();

  // The row opens the due diligence, unless the click was on one of its own
  // links (a questionnaire's answers, its synthesis) or ended a text selection.
  const openRow = (event, session) => {
    if (event.target.closest('a, button')) return;
    if (window.getSelection()?.toString()) return;
    navigate(sessionUrl(session));
  };

  return (
    <div className={tableStyles.wrapper}>
      <table className={`${tableStyles.table} ${tableStyles.inPanel} ${EDGES}`}>
        <caption className="sr-only">Due diligences</caption>
        <thead className={tableStyles.thead}>
          <tr>
            <th scope="col" className={tableStyles.th}>
              Due diligence
            </th>
            <th scope="col" className={tableStyles.th}>
              Questionnaires
            </th>
            <th scope="col" className={tableStyles.th}>
              Status
            </th>
            <th scope="col" className={`${tableStyles.th} w-44`}>
              Progress
            </th>
            <th scope="col" className={tableStyles.th}>
              Last activity
            </th>
            <th scope="col" className={`${tableStyles.th} w-10`}>
              <span className="sr-only">Open</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {sessions.map(session => {
            const activity = lastActivity(session);
            return (
              <tr
                key={session.id}
                onClick={event => openRow(event, session)}
                className={`${tableStyles.row} group cursor-pointer`}
              >
                <td className={TD}>
                  <SessionTitle session={session} showOwner={showOwner} />
                </td>
                <td className={TD}>
                  <QuestionnaireList session={session} />
                </td>
                <td className={`${TD} whitespace-nowrap`}>
                  <StatusBadge status={session.status} />
                  <StalledNote runs={stalledRuns(session)} />
                </td>
                <td className={TD}>
                  <QuestionsProgress answered={session.answered} total={session.questions} />
                </td>
                <td
                  className={`${TD} whitespace-nowrap text-sm text-content-secondary tabular-nums`}
                  title={activity.title}
                >
                  {activity.label}
                </td>
                <td className={TD}>
                  <ChevronRightIcon
                    className="mt-0.5 h-4 w-4 text-content-muted transition-colors group-hover:text-content"
                    aria-hidden="true"
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

/** Below the large screens: one card per due diligence, the whole card opens it. */
const Cards = ({ sessions, showOwner }) => (
  <ul className="divide-y divide-border">
    {sessions.map(session => {
      const activity = lastActivity(session);
      return (
        <li
          key={session.id}
          className="relative px-4 py-4 transition-colors duration-150 hover:bg-surface-hover sm:px-5"
        >
          <div className="flex items-start justify-between gap-3">
            <SessionTitle session={session} showOwner={showOwner} stretched />
            <StatusBadge status={session.status} className="shrink-0" />
          </div>
          <StalledNote runs={stalledRuns(session)} />
          <div className="mt-3 max-w-md">
            <QuestionsProgress answered={session.answered} total={session.questions} />
          </div>
          <div className="mt-2">
            <QuestionnaireList session={session} />
          </div>
          <p className="mt-2 text-xs text-content-muted tabular-nums" title={activity.title}>
            Last activity {activity.label}
          </p>
        </li>
      );
    })}
  </ul>
);

/**
 * The due diligences: a table on a large screen, cards on a smaller one.
 * `showOwner`: an admin sees who created each one.
 */
export const SessionsList = ({ sessions, showOwner }) => (
  <>
    <div className="hidden lg:block">
      <Table sessions={sessions} showOwner={showOwner} />
    </div>
    <div className="lg:hidden">
      <Cards sessions={sessions} showOwner={showOwner} />
    </div>
  </>
);
