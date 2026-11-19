import {
  CheckIcon,
  EyeIcon,
  ShieldCheckIcon,
  TrashIcon,
  UserIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { getToneStyles } from '@/shared/lib/status';
import { Button, tableStyles } from '@/shared/ui';
import { formatUserDate, roleBadge } from '../lib/display';

const COLUMNS = ['User', 'Company', 'Role', 'Status', 'Last Login', 'Actions'];

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
        </tr>
      </thead>
      <tbody>
        {users.users.length === 0 ? (
          <tr>
            <td colSpan={COLUMNS.length} className={tableStyles.empty}>
              {search ? `No users found matching "${search}"` : 'No users found'}
            </td>
          </tr>
        ) : (
          users.users.map((user, index) => (
            <tr key={user.id} className={`${tableStyles.row} ${tableStyles.rowAlt(index)}`}>
              <td className={`${tableStyles.td} whitespace-nowrap`}>
                <div className="flex items-center">
                  <div className="flex-shrink-0 h-10 w-10 rounded-full bg-surface-hover flex items-center justify-center">
                    <UserIcon className="h-6 w-6 text-content-secondary" />
                  </div>
                  <div className="ml-3">
                    <div className="text-sm font-medium text-content">
                      {user.full_name || 'Unknown'}
                    </div>
                    <div className="text-xs text-content-muted">@{user.username}</div>
                    <div className="text-xs text-content-muted">{user.email}</div>
                  </div>
                </div>
              </td>
              <td className={`${tableStyles.td} whitespace-nowrap text-content`}>
                {user.company || '-'}
              </td>
              <td className={`${tableStyles.td} whitespace-nowrap`}>
                <select
                  value={user.role}
                  onChange={event => users.setRole(user, event.target.value)}
                  disabled={users.isBusy('role', user)}
                  aria-label={`Role of ${user.username}`}
                  className={`form-input text-xs font-medium px-2 py-1 rounded-full ${roleBadge(user.role)}`}
                >
                  <option value="analyst">Analyst</option>
                  <option value="admin">Admin</option>
                </select>
              </td>
              <td className={`${tableStyles.td} whitespace-nowrap`}>
                <button
                  onClick={() => users.setActive(user, !user.is_active)}
                  disabled={users.isBusy('status', user)}
                  title={user.is_active ? 'Deactivate' : 'Activate'}
                  className={`inline-flex items-center rounded-xl border px-2 py-0.5 text-xs font-medium hover:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed ${
                    getToneStyles(user.is_active ? 'success' : 'error').badge
                  }`}
                >
                  {user.is_active ? (
                    <CheckIcon className="w-3 h-3 mr-1" />
                  ) : (
                    <XMarkIcon className="w-3 h-3 mr-1" />
                  )}
                  {user.is_active ? 'Active' : 'Inactive'}
                </button>
              </td>
              <td className={`${tableStyles.td} whitespace-nowrap text-content tabular-nums`}>
                {formatUserDate(user.last_login)}
              </td>
              <td className={`${tableStyles.td} whitespace-nowrap text-content-muted`}>
                <div className="flex items-center space-x-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={EyeIcon}
                    onClick={() => onView(user)}
                    title="View user details"
                    aria-label={`View ${user.username}`}
                  />
                  {user.role === 'admin' ? (
                    <ShieldCheckIcon className="h-4 w-4 text-accent-gold" title="Administrator" />
                  ) : (
                    <Button
                      variant="danger"
                      size="sm"
                      icon={TrashIcon}
                      onClick={() => users.remove(user)}
                      disabled={users.isBusy('delete', user)}
                      title="Delete user"
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
