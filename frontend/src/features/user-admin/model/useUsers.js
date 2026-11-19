import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { adminAPI } from '@/entities/user';
import { errorMessage } from '@/shared/api';
import { useConfirm } from '@/shared/lib/confirm';
import { useDebounce } from '@/shared/lib/hooks';

const PER_PAGE = 20;

/**
 * The accounts, a page at a time, searched by the server: the page used to
 * fetch the first 100 and filter those, so the 101st account never showed.
 * Role, activation and deletion, each with its own busy flag.
 */
export const useUsers = () => {
  const confirm = useConfirm();
  const [search, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [result, setResult] = useState({ users: [], total: 0, total_pages: 0 });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState({});
  const term = useDebounce(search, 300).trim();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await adminAPI.getUsers({
        page,
        per_page: PER_PAGE,
        search: term || undefined,
      });
      setResult(response.data);
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to load users'));
    } finally {
      setLoading(false);
    }
  }, [page, term]);

  useEffect(() => {
    load();
  }, [load]);

  const setSearch = value => {
    setSearchTerm(value);
    setPage(1);
  };

  // Runs `action` with the account flagged busy for `what`, then patches it.
  const run = async (user, what, action, patch, failure) => {
    const key = `${what}_${user.id}`;
    setBusy(previous => ({ ...previous, [key]: true }));
    try {
      const response = await action();
      if (response?.data?.message) toast.success(response.data.message);
      setResult(previous => ({
        ...previous,
        users: previous.users.map(item => (item.id === user.id ? { ...item, ...patch } : item)),
      }));
    } catch (error) {
      toast.error(errorMessage(error, failure));
    } finally {
      setBusy(previous => ({ ...previous, [key]: false }));
    }
  };

  const setRole = (user, role) =>
    run(
      user,
      'role',
      () => adminAPI.updateUserRole(user.id, role),
      { role },
      'Failed to update role'
    );

  const setActive = (user, isActive) =>
    run(
      user,
      'status',
      () => adminAPI.updateUserStatus(user.id, isActive),
      { is_active: isActive },
      'Failed to update status'
    );

  const remove = async user => {
    const confirmed = await confirm({
      title: 'Delete user',
      message:
        `Delete ${user.full_name || user.email} (@${user.username})? ` +
        'An account that owns sessions or documents cannot be deleted: deactivate it instead. ' +
        'This cannot be undone.',
      confirmLabel: 'Delete',
      danger: true,
    });
    if (!confirmed) return;
    const key = `delete_${user.id}`;
    setBusy(previous => ({ ...previous, [key]: true }));
    try {
      await adminAPI.deleteUser(user.id);
      toast.success('User deleted successfully');
      await load();
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to delete user'));
    } finally {
      setBusy(previous => ({ ...previous, [key]: false }));
    }
  };

  return {
    users: result.users,
    total: result.total,
    totalPages: result.total_pages,
    page,
    setPage,
    search,
    setSearch,
    loading,
    isBusy: (what, user) => Boolean(busy[`${what}_${user.id}`]),
    setRole,
    setActive,
    remove,
  };
};
