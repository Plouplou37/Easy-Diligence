import { useState } from 'react';
import {
  AtSymbolIcon,
  BriefcaseIcon,
  CheckIcon,
  EnvelopeIcon,
  UserCircleIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '@/entities/viewer';
import { Button, Input, panel, sectionHeader } from '@/shared/ui';

// What the user may change about themselves (UserUpdate in models/user.py).
const editable = user => ({
  full_name: user?.full_name || '',
  email: user?.email || '',
  company: user?.company || '',
  phone: user?.phone || '',
});

const Detail = ({ label, icon: Icon, children }) => (
  <div>
    <p className="eyebrow mb-1">{label}</p>
    <p className="text-sm text-content flex items-center">
      {Icon && <Icon className="w-4 h-4 mr-2 text-content-muted" />}
      {children}
    </p>
  </div>
);

/** The user's own account: read, or edited in place. */
export const ProfileDetails = () => {
  const { user, updateProfile } = useAuth();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(() => editable(user));
  const [saving, setSaving] = useState(false);

  const change = event => {
    const { name, value } = event.target;
    setForm(previous => ({ ...previous, [name]: value }));
  };

  const cancel = () => {
    setForm(editable(user));
    setEditing(false);
  };

  const save = async event => {
    event.preventDefault();
    setSaving(true);
    const result = await updateProfile(form);
    setSaving(false);
    if (result.success) setEditing(false);
  };

  return (
    <form className={panel.base} onSubmit={save}>
      <div className={panel.header}>
        <div className="flex items-center justify-between gap-4">
          <div className={`${sectionHeader.wrapper} flex-1 min-w-0`}>
            <h2 className={sectionHeader.title}>Profile Information</h2>
            <div className={sectionHeader.hairline} />
          </div>
          {editing ? (
            <div className="flex space-x-2">
              <Button type="submit" variant="success" icon={CheckIcon} loading={saving}>
                Save
              </Button>
              <Button type="button" variant="secondary" onClick={cancel}>
                Cancel
              </Button>
            </div>
          ) : (
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setForm(editable(user));
                setEditing(true);
              }}
            >
              Edit Profile
            </Button>
          )}
        </div>
      </div>

      <div className={panel.body}>
        <div className="flex items-center mb-6">
          <UserCircleIcon className="h-20 w-20 text-content-muted" />
          <div className="ml-4">
            <h3 className="text-lg font-medium text-content">{user?.full_name}</h3>
            <p className="text-sm text-content-secondary flex items-center">
              <AtSymbolIcon className="w-3 h-3 mr-1" />
              {user?.username}
            </p>
          </div>
        </div>

        {editing ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Input
              label="Full Name"
              name="full_name"
              value={form.full_name}
              onChange={change}
              autoComplete="name"
            />
            <Input
              label="Email Address"
              name="email"
              type="email"
              value={form.email}
              onChange={change}
              required
            />
            <Input
              label="Company"
              name="company"
              value={form.company}
              onChange={change}
              placeholder="Your company name"
            />
            <Input
              label="Phone Number"
              name="phone"
              type="tel"
              value={form.phone}
              onChange={change}
              placeholder="Your phone number"
            />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Detail label="Full Name">{user?.full_name || 'Not specified'}</Detail>
            <Detail label="Email Address" icon={EnvelopeIcon}>
              {user?.email}
            </Detail>
            <Detail label="Company" icon={BriefcaseIcon}>
              {user?.company || 'Not specified'}
            </Detail>
            <Detail label="Phone Number">{user?.phone || 'Not specified'}</Detail>
          </div>
        )}

        <div className="mt-6 pt-6 border-t border-border grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <span className="eyebrow">Account Type:</span>
            <span className="ml-2 text-content">
              {user?.role === 'admin' ? 'Administrator' : 'Analyst'}
            </span>
          </div>
          {user?.created_at && (
            <div>
              <span className="eyebrow">Member Since:</span>
              <span className="ml-2 text-content">
                {new Date(user.created_at).toLocaleDateString()}
              </span>
            </div>
          )}
        </div>
      </div>
    </form>
  );
};
