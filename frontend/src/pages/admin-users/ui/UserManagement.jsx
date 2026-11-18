import React, { useState, useEffect, useMemo } from 'react';
import {
  ShieldCheckIcon,
  UserIcon,
  CheckIcon,
  XMarkIcon,
  EyeIcon,
  PencilIcon,
  TrashIcon
} from '@heroicons/react/24/outline';
import { adminAPI } from '@/entities/user';
import toast from 'react-hot-toast';
import { useDebounce } from '@/shared/lib/hooks';
import {
  Button,
  Badge,
  LoadingSpinner,
  PageHeader,
  SearchInput,
  field,
  modalStyles,
  pageLayout,
  panel,
  tableStyles,
} from '@/shared/ui';
import { getToneStyles } from '@/shared/lib/status';

const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [allUsers, setAllUsers] = useState([]); // Store all users for client-side filtering
  const [updating, setUpdating] = useState({});
  const [selectedUser, setSelectedUser] = useState(null);
  const [showUserModal, setShowUserModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [userToDelete, setUserToDelete] = useState(null);

  // Debounced search for performance
  const debouncedSearch = useDebounce(search, 300);

  const fetchAllUsers = async () => {
    try {
      setLoading(true);
      const response = await adminAPI.getUsers({ per_page: 100 });
      setAllUsers(response.data.users);
    } catch (error) {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  // Filter users based on debounced search term (better performance)
  const filteredUsers = useMemo(() => {
    if (!debouncedSearch.trim()) {
      return allUsers;
    }

    const searchLower = debouncedSearch.toLowerCase().trim();
    return allUsers.filter(user =>
      (user.full_name?.toLowerCase() || '').includes(searchLower) ||
      (user.username?.toLowerCase() || '').includes(searchLower) ||
      (user.email?.toLowerCase() || '').includes(searchLower) ||
      (user.company?.toLowerCase() || '').includes(searchLower)
    );
  }, [allUsers, debouncedSearch]);

  // Paginate filtered users
  const usersPerPage = 20;
  const paginatedUsers = useMemo(() => {
    const startIndex = (currentPage - 1) * usersPerPage;
    const endIndex = startIndex + usersPerPage;
    return filteredUsers.slice(startIndex, endIndex);
  }, [filteredUsers, currentPage]);

  // Calculate total pages for filtered results
  const totalFilteredPages = useMemo(() => {
    return Math.ceil(filteredUsers.length / usersPerPage);
  }, [filteredUsers.length]);

  const updateUserRole = async (userId, newRole) => {
    try {
      setUpdating(prev => ({ ...prev, [`role_${userId}`]: true }));

      const response = await adminAPI.updateUserRole(userId, newRole);
      toast.success(response.data.message);

      setAllUsers(prevUsers =>
        prevUsers.map(user =>
          user.id === userId ? { ...user, role: newRole } : user
        )
      );
    } catch (error) {
      toast.error(error.response?.data?.detail || error.message || 'Failed to update role');
    } finally {
      setUpdating(prev => ({ ...prev, [`role_${userId}`]: false }));
    }
  };

  const updateUserStatus = async (userId, isActive) => {
    try {
      setUpdating(prev => ({ ...prev, [`status_${userId}`]: true }));

      const response = await adminAPI.updateUserStatus(userId, isActive);
      toast.success(response.data.message);

      setAllUsers(prevUsers =>
        prevUsers.map(user =>
          user.id === userId ? { ...user, is_active: isActive } : user
        )
      );
    } catch (error) {
      toast.error(error.response?.data?.detail || error.message || 'Failed to update status');
    } finally {
      setUpdating(prev => ({ ...prev, [`status_${userId}`]: false }));
    }
  };

  const deleteUser = async (userId) => {
    try {
      setUpdating(prev => ({ ...prev, [`delete_${userId}`]: true }));

      await adminAPI.deleteUser(userId);
      toast.success('User deleted successfully');

      setAllUsers(prevUsers => prevUsers.filter(user => user.id !== userId));
      setShowDeleteModal(false);
      setUserToDelete(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || error.message || 'Failed to delete user');
    } finally {
      setUpdating(prev => ({ ...prev, [`delete_${userId}`]: false }));
    }
  };

  // View user details
  const viewUserDetails = (user) => {
    setSelectedUser(user);
    setShowUserModal(true);
  };

  // Open delete confirmation
  const openDeleteConfirm = (user) => {
    setUserToDelete(user);
    setShowDeleteModal(true);
  };

  // Handle search input change
  const handleSearchChange = (value) => {
    setSearch(value);
    setCurrentPage(1); // Reset to first page when searching
  };

  // Load users on component mount
  useEffect(() => {
    fetchAllUsers();
  }, []);

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Get role badge style
  const getRoleBadgeStyle = (role) => {
    switch (role) {
      case 'admin':
        return getToneStyles('brand').badge;
      case 'analyst':
        return getToneStyles('info').badge;
      default:
        return getToneStyles('neutral').badge;
    }
  };

  return (
    <>
      <div className={pageLayout.container}>
        <PageHeader
          breadcrumb={[{ label: 'User Management' }]}
          title="User Management"
          subtitle="Roles and access of the application's accounts"
          meta={search ? `${filteredUsers.length} of ${allUsers.length} users` : `${allUsers.length} users total`}
        />

        <div className={`${panel.base} p-5`}>
          <SearchInput
            placeholder="Search users by name, email, username, or company..."
            value={search}
            onChange={handleSearchChange}
          />
        </div>

        {/* Users Table */}
        <div className={`${panel.base} overflow-hidden`}>
          {loading ? (
            <div className="py-12">
              <LoadingSpinner text="Loading users..." />
            </div>
          ) : (
            <div className={tableStyles.wrapper}>
              <table className={`${tableStyles.table} ${tableStyles.inPanel}`}>
                <thead className={tableStyles.thead}>
                  <tr>
                    <th className={tableStyles.th}>
                      User
                    </th>
                    <th className={tableStyles.th}>
                      Company
                    </th>
                    <th className={tableStyles.th}>
                      Role
                    </th>
                    <th className={tableStyles.th}>
                      Status
                    </th>
                    <th className={tableStyles.th}>
                      Last Login
                    </th>
                    <th className={tableStyles.th}>
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedUsers.length === 0 && !loading ? (
                    <tr>
                      <td colSpan="6" className={tableStyles.empty}>
                        {search ? `No users found matching "${search}"` : 'No users found'}
                      </td>
                    </tr>
                  ) : (
                    paginatedUsers.map((user, index) => (
                    <tr key={user.id} className={`${tableStyles.row} ${tableStyles.rowAlt(index)}`}>
                      <td className={`${tableStyles.td} whitespace-nowrap`}>
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-10 w-10">
                            <div className="h-10 w-10 rounded-full bg-surface-hover flex items-center justify-center">
                              <UserIcon className="h-6 w-6 text-content-secondary" />
                            </div>
                          </div>
                          <div className="ml-3">
                            <div className="text-sm font-medium text-content">
                              {user.full_name || 'Unknown'}
                            </div>
                            <div className="text-xs text-content-muted">
                              @{user.username}
                            </div>
                            <div className="text-xs text-content-muted">
                              {user.email}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className={`${tableStyles.td} whitespace-nowrap text-content`}>
                        {user.company || '-'}
                      </td>
                      <td className={`${tableStyles.td} whitespace-nowrap`}>
                        <select
                          value={user.role}
                          onChange={(e) => updateUserRole(user.id, e.target.value)}
                          disabled={updating[`role_${user.id}`]}
                          className={`form-input text-xs font-medium px-2 py-1 rounded-full ${getRoleBadgeStyle(user.role)}`}
                        >
                          <option value="analyst">Analyst</option>
                          <option value="admin">Admin</option>
                        </select>
                      </td>
                      <td className={`${tableStyles.td} whitespace-nowrap`}>
                        <button
                          onClick={() => updateUserStatus(user.id, !user.is_active)}
                          disabled={updating[`status_${user.id}`]}
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
                        {formatDate(user.last_login)}
                      </td>
                      <td className={`${tableStyles.td} whitespace-nowrap text-content-muted`}>
                        <div className="flex items-center space-x-2">
                          {/* View Details */}
                          <button
                            onClick={() => viewUserDetails(user)}
                            className="p-1 rounded-md text-content-muted hover:text-accent-blue transition-colors"
                            title="View user details"
                          >
                            <EyeIcon className="h-4 w-4" />
                          </button>

                          {/* Edit User (placeholder for future feature) */}
                          <button
                            onClick={() => toast('Edit user feature coming soon!')}
                            className="p-1 rounded-md text-content-muted hover:text-theme-success transition-colors"
                            title="Edit user"
                          >
                            <PencilIcon className="h-4 w-4" />
                          </button>

                          {/* Delete User (only show for non-admin users) */}
                          {user.role !== 'admin' && (
                            <button
                              onClick={() => openDeleteConfirm(user)}
                              disabled={updating[`delete_${user.id}`]}
                              className="p-1 rounded-md text-content-muted hover:text-theme-error transition-colors disabled:opacity-50"
                              title="Delete user"
                            >
                              <TrashIcon className="h-4 w-4" />
                            </button>
                          )}

                          {/* Admin indicator */}
                          {user.role === 'admin' && (
                            <ShieldCheckIcon className="h-4 w-4 text-accent-gold" title="Administrator" />
                          )}
                        </div>
                      </td>
                    </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalFilteredPages > 1 && (
            <div className="px-5 py-3 border-t border-border">
              <div className="flex items-center justify-between">
                <div className="text-sm text-content-secondary">
                  Page {currentPage} of {totalFilteredPages}
                  {search && (
                    <span className="ml-2 text-content-muted">({filteredUsers.length} filtered results)</span>
                  )}
                </div>
                <div className="flex space-x-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setCurrentPage(currentPage - 1)}
                    disabled={currentPage <= 1}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setCurrentPage(currentPage + 1)}
                    disabled={currentPage >= totalFilteredPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* User Details Modal */}
        {showUserModal && selectedUser && (
          <div className={modalStyles.overlay}>
            <div className={`${modalStyles.panel} max-w-2xl`}>
              <div className={modalStyles.header}>
                <h3 className={modalStyles.title}>
                  User Details
                </h3>
                <button
                  onClick={() => setShowUserModal(false)}
                  className={modalStyles.close}
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>

              <div className={`${modalStyles.body} grid grid-cols-1 md:grid-cols-2 gap-4`}>
                <div className="space-y-3">
                  <div>
                    <label className={field.label}>Full Name</label>
                    <p className="text-sm text-content">{selectedUser.full_name || 'Not specified'}</p>
                  </div>
                  <div>
                    <label className={field.label}>Username</label>
                    <p className="text-sm text-content">@{selectedUser.username}</p>
                  </div>
                  <div>
                    <label className={field.label}>Email</label>
                    <p className="text-sm text-content">{selectedUser.email}</p>
                  </div>
                  <div>
                    <label className={field.label}>Company</label>
                    <p className="text-sm text-content">{selectedUser.company || 'Not specified'}</p>
                  </div>
                </div>

                <div className="space-y-3">
                  <div>
                    <label className={field.label}>Role</label>
                    <span className={`inline-flex items-center rounded-xl border px-2 py-0.5 text-xs font-medium ${getRoleBadgeStyle(selectedUser.role)}`}>
                      {selectedUser.role}
                    </span>
                  </div>
                  <div>
                    <label className={field.label}>Status</label>
                    <span className={`inline-flex items-center rounded-xl border px-2 py-0.5 text-xs font-medium ${
                      getToneStyles(selectedUser.is_active ? 'success' : 'error').badge
                    }`}>
                      {selectedUser.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div>
                    <label className={field.label}>Last Login</label>
                    <p className="text-sm text-content">{formatDate(selectedUser.last_login)}</p>
                  </div>
                  <div>
                    <label className={field.label}>Created</label>
                    <p className="text-sm text-content" title={`User ID: ${selectedUser.id}`}>{formatDate(selectedUser.created_at)}</p>
                  </div>
                </div>
              </div>

              <div className={modalStyles.footer}>
                <Button
                  variant="secondary"
                  onClick={() => setShowUserModal(false)}
                >
                  Close
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {showDeleteModal && userToDelete && (
          <div className={modalStyles.overlay}>
            <div className={`${modalStyles.panel} max-w-md`}>
              <div className={modalStyles.header}>
                <h3 className="text-base font-semibold text-theme-error">
                  Delete User
                </h3>
                <button
                  onClick={() => setShowDeleteModal(false)}
                  className={modalStyles.close}
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>

              <div className={modalStyles.body}>
                <p className="text-sm text-content-secondary">
                  Are you sure you want to delete the user <strong>{userToDelete.full_name}</strong> (@{userToDelete.username})?
                </p>
                <p className="text-sm text-theme-error mt-2">
                  This action cannot be undone.
                </p>
              </div>

              <div className={modalStyles.footer}>
                <Button
                  variant="secondary"
                  onClick={() => setShowDeleteModal(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  onClick={() => deleteUser(userToDelete.id)}
                  disabled={updating[`delete_${userToDelete.id}`]}
                  loading={updating[`delete_${userToDelete.id}`]}
                >
                  {updating[`delete_${userToDelete.id}`] ? 'Deleting...' : 'Delete User'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default UserManagement;