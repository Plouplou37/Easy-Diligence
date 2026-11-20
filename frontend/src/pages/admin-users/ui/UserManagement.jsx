import { useState } from 'react';
import { PlusIcon } from '@heroicons/react/24/outline';
import { CreateUserModal, UserDetailsModal, UsersTable, useUsers } from '@/features/user-admin';
import { Button, LoadingSpinner, PageHeader, SearchInput, pageLayout, panel } from '@/shared/ui';

const UserManagement = () => {
  const users = useUsers();
  const [viewed, setViewed] = useState(null);
  const [creating, setCreating] = useState(false);
  const { page, totalPages } = users;

  return (
    <div className={pageLayout.container}>
      <PageHeader
        breadcrumb={[{ label: 'User Management' }]}
        title="User Management"
        subtitle="Roles and access of the application's accounts"
        meta={users.search ? `${users.total} matching users` : `${users.total} users total`}
        actions={
          <Button variant="primary" icon={PlusIcon} onClick={() => setCreating(true)}>
            Create user
          </Button>
        }
      />

      <div className={`${panel.base} p-5`}>
        <SearchInput
          placeholder="Search users by name, email, username, or company..."
          value={users.search}
          onChange={users.setSearch}
        />
      </div>

      <div className={`${panel.base} overflow-hidden`}>
        {users.loading && users.users.length === 0 ? (
          <div className="py-12">
            <LoadingSpinner text="Loading users..." />
          </div>
        ) : (
          <UsersTable users={users} search={users.search} onView={setViewed} />
        )}

        {totalPages > 1 && (
          <div className="px-5 py-3 border-t border-border flex items-center justify-between">
            <div className="text-sm text-content-secondary tabular-nums">
              Page {page} of {totalPages}
            </div>
            <div className="flex space-x-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => users.setPage(page - 1)}
                disabled={page <= 1}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                size="sm"
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
