import { useMemo } from 'react';
import { UserIcon, UsersIcon } from '@heroicons/react/24/outline';
import { IN_PROGRESS_STATUSES } from '@/entities/execution';
import { Badge, Card, tableStyles } from '@/shared/ui';

// Per-user counts, from the dashboard's own data.
const byUser = (sessions) => {
  const users = new Map();
  sessions.forEach((session) => {
    const userId = session.created_by || session.assigned_to;
    if (!userId) return;
    if (!users.has(userId)) {
      users.set(userId, {
        username: session.created_by_username || `User ${userId}`,
        total: 0,
        completed: 0,
        running: 0,
        toReview: 0,
      });
    }
    const stats = users.get(userId);
    stats.total += 1;
    stats.toReview += session.toReview;
    if (session.status === 'completed') stats.completed += 1;
    else if (IN_PROGRESS_STATUSES.includes(session.status)) stats.running += 1;
  });
  return [...users];
};

/** For admins: each user's sessions, finished, running, and answers to review. */
export const UserStatsTable = ({ sessions }) => {
  const rows = useMemo(() => byUser(sessions), [sessions]);
  if (rows.length === 0) return null;

  return (
    <Card
      title={
        <>
          <UsersIcon className="h-4 w-4 text-content-muted" />
          User Analytics
        </>
      }
      noPadding
    >
      <div className={tableStyles.wrapper}>
        <table className={`${tableStyles.table} ${tableStyles.inPanel}`}>
          <thead className={tableStyles.thead}>
            <tr>
              <th className={tableStyles.th}>User</th>
              <th className={tableStyles.thCenter}>Sessions</th>
              <th className={tableStyles.thCenter}>Completed</th>
              <th className={tableStyles.thCenter}>In Progress</th>
              <th className={tableStyles.thCenter}>Answers to Review</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([userId, stats], index) => (
              <tr key={userId} className={`${tableStyles.row} ${tableStyles.rowAlt(index)}`}>
                <td className={tableStyles.td}>
                  <div className="flex items-center gap-2">
                    <UserIcon className="h-4 w-4 text-content-muted" />
                    <span className="text-sm font-medium">{stats.username}</span>
                  </div>
                </td>
                <td className={`${tableStyles.tdCenter} tabular-nums`}>{stats.total}</td>
                <td className={tableStyles.tdCenter}>
                  <Badge variant="success">{stats.completed}</Badge>
                </td>
                <td className={tableStyles.tdCenter}>
                  <Badge variant="info">{stats.running}</Badge>
                </td>
                <td className={`${tableStyles.tdCenter} tabular-nums`}>{stats.toReview}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};
