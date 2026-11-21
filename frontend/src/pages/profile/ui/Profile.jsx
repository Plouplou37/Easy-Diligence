import { useState } from 'react';
import { KeyIcon } from '@heroicons/react/24/outline';
import { useAuth } from '@/entities/viewer';
import { ChangePasswordModal, ProfileDetails } from '@/features/auth';
import { Badge, Button, PageHeader, pageLayout, panel } from '@/shared/ui';

/** The account's initials: from its full name, else its username. */
const initialsOf = user =>
  (user?.full_name || user?.username || '?')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part[0].toUpperCase())
    .join('') || '?';

/** Who is signed in, at a glance. */
const Identity = ({ user }) => (
  <aside
    aria-label="Your account"
    className={`${panel.base} min-w-0 flex-[1_1_260px] p-5 text-center`}
  >
    <span
      className="mx-auto inline-flex h-16 w-16 items-center justify-center rounded-full border border-border bg-surface-hover text-lg font-semibold text-content"
      aria-hidden="true"
    >
      {initialsOf(user)}
    </span>
    <p className="mt-3 break-words text-base font-semibold text-content">
      {user?.full_name || user?.username}
    </p>
    <p className="break-words text-sm text-content-secondary">@{user?.username}</p>
    <div className="mt-3 flex justify-center">
      <Badge variant={user?.role === 'admin' ? 'info' : 'neutral'}>
        {user?.role === 'admin' ? 'Administrator' : 'Analyst'}
      </Badge>
    </div>
    {user?.created_at && (
      <p className="mt-4 border-t border-border pt-4 text-xs tabular-nums text-content-muted">
        Member since {new Date(user.created_at).toLocaleDateString()}
      </p>
    )}
  </aside>
);

const Profile = () => {
  const { user } = useAuth();
  const [changingPassword, setChangingPassword] = useState(false);

  return (
    <div className={pageLayout.container}>
      <PageHeader title="Profile" subtitle="Your account details and your password." />

      <div className="flex flex-wrap items-start gap-6">
        <Identity user={user} />

        <div className="min-w-0 flex-[999_1_520px] space-y-6">
          <ProfileDetails />

          <section aria-label="Password" className={`${panel.base} overflow-hidden`}>
            <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
              <div className="min-w-0">
                <h2 className="text-base font-semibold text-content">Password</h2>
                <p className="mt-0.5 text-sm text-content-muted">
                  Changing it signs you out everywhere: you then sign in with the new one.
                </p>
              </div>
              <Button onClick={() => setChangingPassword(true)} variant="secondary" icon={KeyIcon}>
                Change password
              </Button>
            </div>
          </section>
        </div>
      </div>

      <ChangePasswordModal isOpen={changingPassword} onClose={() => setChangingPassword(false)} />
    </div>
  );
};

export default Profile;
