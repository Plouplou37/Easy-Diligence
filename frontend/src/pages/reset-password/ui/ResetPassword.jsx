import { Link, useSearchParams } from 'react-router-dom';
import { AuthShell, ResetPasswordForm } from '@/features/auth';

/**
 * Where the link of a reset e-mail leads: /reset-password?token=…
 * The token stays in the address: a reload must not lose it, and it is
 * worthless once used (it is tied to the password it replaces) or after 24 h.
 */
const ResetPassword = () => {
  const [searchParams] = useSearchParams();

  return (
    <AuthShell
      title="Choose a new password"
      subtitle={
        <>
          Or{' '}
          <Link to="/login" className="text-link">
            back to sign in
          </Link>
        </>
      }
    >
      <ResetPasswordForm token={searchParams.get('token')} />
    </AuthShell>
  );
};

export default ResetPassword;
