import { useState } from 'react';
import { EnvelopeIcon, LockClosedIcon } from '@heroicons/react/24/outline';
import { useAuth } from '@/entities/viewer';
import { Button, Input, PasswordInput } from '@/shared/ui';
import { ForgotPasswordModal } from './ForgotPasswordModal';

/** E-mail and password; the reset link from there. */
export const LoginForm = () => {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [forgotOpen, setForgotOpen] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    await login(email, password);
    setLoading(false);
  };

  return (
    <>
      <form className="space-y-6" onSubmit={submit}>
        <div className="space-y-5">
          <Input
            id="email"
            name="email"
            label="Email address"
            type="email"
            autoComplete="email"
            required
            leftIcon={EnvelopeIcon}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
          />
          <PasswordInput
            id="password"
            name="password"
            label="Password"
            autoComplete="current-password"
            required
            leftIcon={LockClosedIcon}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="••••••••"
          />
          <div className="text-sm text-right">
            <button type="button" onClick={() => setForgotOpen(true)} className="text-link">
              Forgot your password?
            </button>
          </div>
        </div>

        <Button type="submit" loading={loading} variant="primary" size="lg" className="w-full">
          Sign in
        </Button>
      </form>

      {/* Mounted when open, so it starts from the address typed above. */}
      {forgotOpen && <ForgotPasswordModal isOpen onClose={() => setForgotOpen(false)} initialEmail={email} />}
    </>
  );
};
