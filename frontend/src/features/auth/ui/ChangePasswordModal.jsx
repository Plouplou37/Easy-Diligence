import { useState } from 'react';
import { PASSWORD_RULE, passwordProblem } from '@/entities/user';
import { useAuth } from '@/entities/viewer';
import { Button, Modal, PasswordInput, modalStyles } from '@/shared/ui';

const EMPTY = { current: '', next: '', confirm: '' };

/** Change one's password. Every session is then closed: sign in again. */
export const ChangePasswordModal = ({ isOpen, onClose }) => {
  const { changePassword } = useAuth();
  const [form, setForm] = useState(EMPTY);
  const [problems, setProblems] = useState({});
  const [saving, setSaving] = useState(false);

  const close = () => {
    setForm(EMPTY);
    setProblems({});
    onClose();
  };

  const change = name => event =>
    setForm(previous => ({ ...previous, [name]: event.target.value }));

  const submit = async event => {
    event.preventDefault();
    const found = {};
    if (!form.current) found.current = 'Enter your current password';
    const weak = passwordProblem(form.next);
    if (weak) found.next = weak;
    if (form.next !== form.confirm) found.confirm = 'New passwords do not match';
    setProblems(found);
    if (Object.keys(found).length > 0) return;

    setSaving(true);
    const result = await changePassword(form.current, form.next);
    setSaving(false);
    if (result.success) close();
  };

  return (
    <Modal isOpen={isOpen} onClose={close} title="Change password" size="sm">
      <form onSubmit={submit} noValidate>
        <p className="mb-5 text-sm text-content-secondary">
          You are then signed out everywhere, and sign in again with the new password.
        </p>
        <div className="space-y-5">
          <PasswordInput
            label="Current password"
            autoComplete="current-password"
            value={form.current}
            onChange={change('current')}
            error={problems.current}
          />
          <PasswordInput
            label="New password"
            autoComplete="new-password"
            value={form.next}
            onChange={change('next')}
            error={problems.next}
            helperText={PASSWORD_RULE}
          />
          <PasswordInput
            label="Confirm the new password"
            autoComplete="new-password"
            value={form.confirm}
            onChange={change('confirm')}
            error={problems.confirm}
          />
        </div>
        <div className={`${modalStyles.footer} -mx-5 -mb-4 mt-6`}>
          <Button type="button" variant="secondary" onClick={close}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={saving}>
            Change password
          </Button>
        </div>
      </form>
    </Modal>
  );
};
