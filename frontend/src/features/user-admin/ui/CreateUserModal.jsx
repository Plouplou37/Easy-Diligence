import { useState } from 'react';
import { PASSWORD_RULE, passwordProblem } from '@/entities/user';
import { Button, Input, Modal, PasswordInput, modalStyles } from '@/shared/ui';

const EMPTY = { full_name: '', username: '', email: '', role: 'analyst', password: '' };

// What each role may do (backend/app/services/authz.py).
const ROLES = [
  {
    value: 'analyst',
    label: 'Analyst',
    text: 'Runs due diligences, and sees their own work and what is shared with them.',
  },
  {
    value: 'admin',
    label: 'Admin',
    text: 'Sees and changes everything, and manages the users.',
  },
];

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
    <Modal isOpen={isOpen} onClose={close} title="New user">
      <form onSubmit={submit} noValidate>
        <p className="mb-5 text-sm text-content-secondary">
          There is no self-registration: you create the account, then pass its provisional password
          on to its user.
        </p>

        <div className="space-y-5">
          <Input
            label="Full name"
            value={form.full_name}
            onChange={set('full_name')}
            autoComplete="off"
          />
          <div className="grid gap-5 sm:grid-cols-2">
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
          </div>

          <fieldset>
            <legend className="mb-1.5 text-sm font-medium text-content">Role</legend>
            <div className="grid gap-3 sm:grid-cols-2">
              {ROLES.map(role => {
                const checked = form.role === role.value;
                return (
                  <label
                    key={role.value}
                    className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3.5 transition-colors ${
                      checked
                        ? 'border-primary bg-primary-dark'
                        : 'border-border-hover bg-surface-bg hover:border-content-muted'
                    }`}
                  >
                    <input
                      type="radio"
                      name="new-user-role"
                      value={role.value}
                      checked={checked}
                      onChange={set('role')}
                      className="mt-1"
                    />
                    <span className="min-w-0">
                      <span className="block text-sm font-semibold text-content">{role.label}</span>
                      <span className="mt-0.5 block text-xs text-content-secondary">
                        {role.text}
                      </span>
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>

          <PasswordInput
            label="Provisional password"
            required
            value={form.password}
            onChange={set('password')}
            error={problems.password}
            helperText={`${PASSWORD_RULE} Pass it on to the user, who changes it in their profile.`}
            autoComplete="new-password"
          />
        </div>

        <div className={`${modalStyles.footer} -mx-5 -mb-4 mt-6`}>
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
