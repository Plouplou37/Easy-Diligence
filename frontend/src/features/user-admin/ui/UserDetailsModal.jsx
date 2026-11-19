import { getToneStyles } from '@/shared/lib/status';
import { Button, Modal, field, modalStyles } from '@/shared/ui';
import { formatUserDate, roleBadge } from '../lib/display';

const Item = ({ label, children, title }) => (
  <div>
    <p className={field.label}>{label}</p>
    <div className="text-sm text-content" title={title}>
      {children}
    </div>
  </div>
);

const pill = 'inline-flex items-center rounded-xl border px-2 py-0.5 text-xs font-medium';

/** Everything known about an account, read only. */
export const UserDetailsModal = ({ user, onClose }) => (
  <Modal isOpen={Boolean(user)} onClose={onClose} title="User Details" size="lg">
    {user && (
      <>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <Item label="Full Name">{user.full_name || 'Not specified'}</Item>
            <Item label="Username">@{user.username}</Item>
            <Item label="Email">{user.email}</Item>
            <Item label="Company">{user.company || 'Not specified'}</Item>
          </div>
          <div className="space-y-3">
            <Item label="Role">
              <span className={`${pill} ${roleBadge(user.role)}`}>{user.role}</span>
            </Item>
            <Item label="Status">
              <span className={`${pill} ${getToneStyles(user.is_active ? 'success' : 'error').badge}`}>
                {user.is_active ? 'Active' : 'Inactive'}
              </span>
            </Item>
            <Item label="Last Login">{formatUserDate(user.last_login)}</Item>
            <Item label="Created" title={`User ID: ${user.id}`}>
              {formatUserDate(user.created_at)}
            </Item>
          </div>
        </div>
        <div className={`${modalStyles.footer} -mx-5 -mb-4 mt-4`}>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </>
    )}
  </Modal>
);
