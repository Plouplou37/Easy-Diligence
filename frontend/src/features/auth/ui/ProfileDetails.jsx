import { useState } from 'react';
import { PencilIcon } from '@heroicons/react/24/outline';
import { useAuth } from '@/entities/viewer';
import { Button, Input, panel } from '@/shared/ui';

// What the user may change about themselves (UserUpdate in models/user.py).
const editable = user => ({
  full_name: user?.full_name || '',
  email: user?.email || '',
  company: user?.company || '',
  phone: user?.phone || '',
});

const Detail = ({ label, children }) => (
  <div className="min-w-0">
    <dt className="text-xs text-content-muted">{label}</dt>
    <dd className="mt-0.5 break-words text-sm text-content">{children}</dd>
  </div>
);

const NotGiven = () => <span className="text-content-muted">Not given</span>;

/** The user's own account details: read, or edited in place. */
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
    <form className={`${panel.base} overflow-hidden`} onSubmit={save}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-content">Account details</h2>
          <p className="mt-0.5 text-sm text-content-muted">
            {editing ? 'Your username cannot change.' : 'How your team sees and reaches you.'}
          </p>
        </div>
        {!editing && (
          <Button
            type="button"
            variant="secondary"
            icon={PencilIcon}
            onClick={() => {
              setForm(editable(user));
              setEditing(true);
            }}
          >
            Edit
          </Button>
        )}
      </div>

      <div className={panel.body}>
        {editing ? (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            <Input
              label="Full name"
              name="full_name"
              value={form.full_name}
              onChange={change}
              autoComplete="name"
            />
            <Input
              label="Email address"
              name="email"
              type="email"
              value={form.email}
              onChange={change}
              autoComplete="email"
              required
            />
            <Input
              label="Company"
              name="company"
              value={form.company}
              onChange={change}
              autoComplete="organization"
            />
            <Input
              label="Phone number"
              name="phone"
              type="tel"
              value={form.phone}
              onChange={change}
              autoComplete="tel"
            />
          </div>
        ) : (
          <dl className="grid grid-cols-1 gap-5 md:grid-cols-2">
            <Detail label="Full name">{user?.full_name || <NotGiven />}</Detail>
            <Detail label="Email address">{user?.email}</Detail>
            <Detail label="Company">{user?.company || <NotGiven />}</Detail>
            <Detail label="Phone number">{user?.phone || <NotGiven />}</Detail>
          </dl>
        )}
      </div>

      {editing && (
        <div className={`${panel.footer} flex justify-end gap-2`}>
          <Button type="button" variant="secondary" onClick={cancel}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={saving}>
            Save changes
          </Button>
        </div>
      )}
    </form>
  );
};
