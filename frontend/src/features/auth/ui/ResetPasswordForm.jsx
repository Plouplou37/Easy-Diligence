import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { ExclamationTriangleIcon, LockClosedIcon } from '@heroicons/react/24/outline';
import { PASSWORD_RULE, passwordProblem } from '@/entities/user';
import { authAPI } from '@/entities/viewer';
import { errorMessage } from '@/shared/api';
import { Button, PasswordInput } from '@/shared/ui';

const LinkProblem = ({ children }) => (
  <div className="alert alert-error space-y-2 text-sm">
    <p className="flex items-start gap-2">
      <ExclamationTriangleIcon className="w-5 h-5 flex-shrink-0" />
      <span>{children}</span>
    </p>
    <p>
      Ask for a new one from the{' '}
      <Link to="/login" className="text-link">
        sign-in page
      </Link>{' '}
      (“Forgot your password?”).
    </p>
  </div>
);

/**
 * A new password, set with the token of a reset e-mail. The token is valid
 * for 24 hours and works once: it is tied to the password it was issued for.
 */
export const ResetPasswordForm = ({ token }) => {
  const navigate = useNavigate();
  const [form, setForm] = useState({ next: '', confirm: '' });
  const [problems, setProblems] = useState({});
  const [refused, setRefused] = useState(null);
  const [saving, setSaving] = useState(false);

  if (!token) {
    return <LinkProblem>This link is incomplete: it carries no reset token.</LinkProblem>;
  }

  const change = name => event =>
    setForm(previous => ({ ...previous, [name]: event.target.value }));

  const submit = async event => {
    event.preventDefault();
    const found = {};
    const weak = passwordProblem(form.next);
    if (weak) found.next = weak;
    if (form.next !== form.confirm) found.confirm = 'Passwords do not match';
    setProblems(found);
    if (Object.keys(found).length > 0) return;

    setSaving(true);
    try {
      await authAPI.confirmPasswordReset(token, form.next);
      toast.success('Password changed. Sign in with your new password.');
      navigate('/login', { replace: true });
    } catch (error) {
      // An expired or used link: the server says which, in words for the user.
      setRefused(errorMessage(error, 'The password could not be changed.'));
      setSaving(false);
    }
  };

  return (
    <form className="space-y-6" onSubmit={submit} noValidate>
      {refused && <LinkProblem>{refused}</LinkProblem>}
      <div className="space-y-5">
        <PasswordInput
          id="new-password"
          label="New password"
          autoComplete="new-password"
          required
          leftIcon={LockClosedIcon}
          value={form.next}
          onChange={change('next')}
          error={problems.next}
          helperText={PASSWORD_RULE}
        />
        <PasswordInput
          id="confirm-password"
          label="Confirm new password"
          autoComplete="new-password"
          required
          leftIcon={LockClosedIcon}
          value={form.confirm}
          onChange={change('confirm')}
          error={problems.confirm}
        />
      </div>
      <Button type="submit" loading={saving} variant="primary" size="lg" className="w-full">
        Change password
      </Button>
    </form>
  );
};
