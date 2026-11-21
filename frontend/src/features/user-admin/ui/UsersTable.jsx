import { ShieldCheckIcon, TrashIcon } from '@heroicons/react/24/outline';
import { Badge, Button, tableStyles } from '@/shared/ui';
import { formatUserDate, initialsOf } from '../lib/display';

const COLUMNS = ['User', 'Company', 'Role', 'Status', 'Last sign-in'];

/**
 * The accounts, with their role and activation editable in place. `users`
 * comes from useUsers; `onView` opens the details.
 */
export const UsersTable = ({ users, search, onView }) => (
  <div className={tableStyles.wrapper}>
    <table className={`${tableStyles.table} ${tableStyles.inPanel}`}>
      <thead className={tableStyles.thead}>
        <tr>
          {COLUMNS.map(column => (
            <th key={column} className={tableStyles.th}>
              {column}
            </th>
          ))}
          <th className={tableStyles.thRight}>
            <span className="sr-only">Actions</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {users.users.length === 0 ? (
          <tr>
            <td colSpan={COLUMNS.length + 1} className={tableStyles.empty}>
              {search ? `No user matches "${search}"` : 'No users yet'}
            </td>
          </tr>
        ) : (
          users.users.map(user => (
            <tr key={user.id} className={tableStyles.row}>
              <td className={`${tableStyles.td} min-w-60`}>
                <div className="flex items-center gap-3">
                  <span
                    className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border bg-surface-hover text-xs font-semibold text-content"
                    aria-hidden="true"
                  >
                    {initialsOf(user)}
                  </span>
                  <div className="min-w-0">
                    <button
                      type="button"
                      onClick={() => onView(user)}
                      className="text-left text-sm font-medium text-content transition-colors hover:text-accent-blue"
                    >
                      {user.full_name || `@${user.username}`}
                    </button>
                    <p className="truncate text-xs text-content-muted">
                      @{user.username} · {user.email}
                    </p>
                  </div>
                </div>
              </td>
              <td className={`${tableStyles.td} whitespace-nowrap text-content-secondary`}>
                {user.company || '—'}
              </td>
              <td className={`${tableStyles.td} whitespace-nowrap`}>
                <select
                  value={user.role}
                  onChange={event => users.setRole(user, event.target.value)}
                  disabled={users.isBusy('role', user)}
                  aria-label={`Role of ${user.username}`}
                  className="form-input h-10 py-1 text-sm"
                >
                  <option value="analyst">Analyst</option>
                  <option value="admin">Admin</option>
                </select>
              </td>
              <td className={`${tableStyles.td} whitespace-nowrap`}>
                {user.is_active ? (
                  <Badge variant="success" dot>
                    Active
                  </Badge>
                ) : (
                  <span title="This account cannot sign in">
                    <Badge variant="neutral" dot>
                      Inactive
                    </Badge>
                  </span>
                )}
              </td>
              <td
                className={`${tableStyles.td} whitespace-nowrap tabular-nums text-content-secondary`}
              >
                {formatUserDate(user.last_login)}
              </td>
              <td className={`${tableStyles.tdRight} whitespace-nowrap`}>
                <div className="flex items-center justify-end gap-1">
                  <Button
                    variant="ghost"
                    onClick={() => onView(user)}
                    aria-label={`Details of ${user.username}`}
                  >
                    Details
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => users.setActive(user, !user.is_active)}
                    loading={users.isBusy('status', user)}
                    title={
                      user.is_active
                        ? 'An inactive account can no longer sign in'
                        : 'Let this account sign in again'
                    }
                    aria-label={`${user.is_active ? 'Deactivate' : 'Activate'} ${user.username}`}
                  >
                    {user.is_active ? 'Deactivate' : 'Activate'}
                  </Button>
                  {user.role === 'admin' ? (
                    <span
                      className="inline-flex h-10 w-10 items-center justify-center text-content-muted"
                      title="An administrator cannot be deleted: make the account an analyst first"
                    >
                      <ShieldCheckIcon className="h-5 w-5" aria-hidden="true" />
                      <span className="sr-only">Administrator: cannot be deleted</span>
                    </span>
                  ) : (
                    <Button
                      variant="danger"
                      size="lg"
                      icon={TrashIcon}
                      onClick={() => users.remove(user)}
                      disabled={users.isBusy('delete', user)}
                      title="Delete this account"
                      aria-label={`Delete ${user.username}`}
                    />
                  )}
                </div>
              </td>
            </tr>
          ))
        )}
      </tbody>
    </table>
  </div>
);
