import { useState } from 'react';
import { PASSWORD_RULE, passwordProblem } from '@/entities/user';
import { Button, Input, Modal, PasswordInput, field, modalStyles } from '@/shared/ui';

const EMPTY = { full_name: '', username: '', email: '', role: 'analyst', password: '' };

// The username rule of the backend (models/user.py, UserProfile).
const USERNAME = /^[a-zA-Z0-9._-]{3,30}$/;

const problemsOf = form => {
  const found = {};
  if (!USERNAME.test(form.username)) {
    found.username = '3 to 30 letters, digits, dots, hyphens or underscores';
  }
  if (!/\S+@\S+\.\S+/.test(form.email)) found.email = 'Please enter a valid email';
  const weak = passwordProblem(form.password);
  if (weak) found.password = weak;
  return found;
};

/**
 * A new account, made by an admin: there is no self-registration. The
 * password is provisional: the admin passes it on, and the user changes it in
 * their profile. `onCreate(account)` resolves to true once created.
 */
export const CreateUserModal = ({ isOpen, onClose, onCreate }) => {
  const [form, setForm] = useState(EMPTY);
  const [problems, setProblems] = useState({});
  const [saving, setSaving] = useState(false);

  const close = () => {
    setForm(EMPTY);
    setProblems({});
    onClose();
  };

  const set = name => event => {
    setForm(previous => ({ ...previous, [name]: event.target.value }));
    if (problems[name]) setProblems(previous => ({ ...previous, [name]: undefined }));
  };

  const submit = async event => {
    event.preventDefault();
    const found = problemsOf(form);
    setProblems(found);
    if (Object.keys(found).length > 0) return;
    setSaving(true);
    const created = await onCreate({ ...form, full_name: form.full_name.trim() || null });
    setSaving(false);
    if (created) close();
  };

  return (
    <Modal isOpen={isOpen} onClose={close} title="Create user">
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Input
          label="Full name"
          value={form.full_name}
          onChange={set('full_name')}
          autoComplete="off"
        />
        <Input
          label="Username"
          required
          value={form.username}
          onChange={set('username')}
          error={problems.username}
          autoComplete="off"
        />
        <Input
          label="Email"
          type="email"
          required
          value={form.email}
          onChange={set('email')}
          error={problems.email}
          autoComplete="off"
        />
        <div>
          <label htmlFor="new-user-role" className={field.label}>
            Role
          </label>
          <select
            id="new-user-role"
            value={form.role}
            onChange={set('role')}
            className="form-input w-full px-3 py-2 text-sm"
          >
            <option value="analyst">Analyst</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <PasswordInput
          label="Provisional password"
          required
          value={form.password}
          onChange={set('password')}
          error={problems.password}
          helperText={`${PASSWORD_RULE} Pass it on to the user, who changes it in their profile.`}
          autoComplete="new-password"
        />
        <div className={`${modalStyles.footer} -mx-5 -mb-4 mt-4`}>
          <Button type="button" variant="secondary" onClick={close}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={saving}>
            Create user
          </Button>
        </div>
      </form>
    </Modal>
  );
};
