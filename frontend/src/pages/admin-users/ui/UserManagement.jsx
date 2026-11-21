import { useState } from 'react';
import { PlusIcon } from '@heroicons/react/24/outline';
import { CreateUserModal, UserDetailsModal, UsersTable, useUsers } from '@/features/user-admin';
import { Button, LoadingSpinner, PageHeader, SearchInput, pageLayout, panel } from '@/shared/ui';

/** The accounts: who can sign in, with which role. Admins only. */
const UserManagement = () => {
  const users = useUsers();
  const [viewed, setViewed] = useState(null);
  const [creating, setCreating] = useState(false);
  const { page, totalPages } = users;
  const count = `${users.total} ${users.search ? 'matching ' : ''}user${users.total === 1 ? '' : 's'}`;

  return (
    <div className={pageLayout.container}>
      <PageHeader
        title="Users"
        subtitle="The accounts that can sign in, their role and their access. There is no self-registration: accounts are created here."
        actions={
          <Button variant="primary" icon={PlusIcon} onClick={() => setCreating(true)}>
            New user
          </Button>
        }
      />

      <div className={`${panel.base} overflow-hidden`}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
          <SearchInput
            className="min-w-0 flex-[0_1_24rem]"
            placeholder="Search by name, email, username or company"
            value={users.search}
            onChange={users.setSearch}
            aria-label="Search the users"
          />
          <p className="text-sm tabular-nums text-content-muted" aria-live="polite">
            {count}
          </p>
        </div>

        {users.loading && users.users.length === 0 ? (
          <div className="py-12">
            <LoadingSpinner text="Loading the users…" />
          </div>
        ) : (
          <UsersTable users={users} search={users.search} onView={setViewed} />
        )}

        {totalPages > 1 && (
          <div className={`${panel.footer} flex flex-wrap items-center justify-between gap-3`}>
            <p className="text-sm tabular-nums text-content-secondary">
              Page {page} of {totalPages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                onClick={() => users.setPage(page - 1)}
                disabled={page <= 1}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                onClick={() => users.setPage(page + 1)}
                disabled={page >= totalPages}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>

      <UserDetailsModal user={viewed} onClose={() => setViewed(null)} />
      <CreateUserModal
        isOpen={creating}
        onClose={() => setCreating(false)}
        onCreate={users.create}
      />
    </div>
  );
};

export default UserManagement;
