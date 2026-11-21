import { Badge, Button, Modal, modalStyles } from '@/shared/ui';
import { formatUserDate, initialsOf, roleOf } from '../lib/display';

const Item = ({ label, children, title }) => (
  <div className="min-w-0">
    <dt className="text-xs text-content-muted">{label}</dt>
    <dd className="mt-0.5 break-words text-sm text-content" title={title}>
      {children}
    </dd>
  </div>
);

/** Everything known about an account, read only. */
export const UserDetailsModal = ({ user, onClose }) => {
  const role = roleOf(user?.role);
  return (
    <Modal isOpen={Boolean(user)} onClose={onClose} title="User details">
      {user && (
        <>
          <div className="flex items-center gap-4">
            <span
              className="inline-flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-border bg-surface-hover text-base font-semibold text-content"
              aria-hidden="true"
            >
              {initialsOf(user)}
            </span>
            <div className="min-w-0">
              <p className="truncate text-lg font-semibold text-content">
                {user.full_name || 'No name given'}
              </p>
              <p className="truncate text-sm text-content-secondary">@{user.username}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Badge variant={role.variant}>{role.label}</Badge>
                {user.is_active ? (
                  <Badge variant="success" dot>
                    Active
                  </Badge>
                ) : (
                  <Badge variant="neutral" dot>
                    Inactive
                  </Badge>
                )}
              </div>
            </div>
          </div>

          <dl className="mt-6 grid gap-x-6 gap-y-4 border-t border-border pt-5 sm:grid-cols-2">
            <Item label="Email">{user.email}</Item>
            <Item label="Company">{user.company || 'Not given'}</Item>
            <Item label="Phone">{user.phone || 'Not given'}</Item>
            <Item label="Last sign-in">{formatUserDate(user.last_login)}</Item>
            <Item label="Created" title={`User ID: ${user.id}`}>
              {formatUserDate(user.created_at)}
            </Item>
          </dl>

          <div className={`${modalStyles.footer} -mx-5 -mb-4 mt-6`}>
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
          </div>
        </>
      )}
    </Modal>
  );
};
