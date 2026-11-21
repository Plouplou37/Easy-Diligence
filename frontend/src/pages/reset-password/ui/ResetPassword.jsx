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
      subtitle="The link of the e-mail works once, for 24 hours."
    >
      <ResetPasswordForm token={searchParams.get('token')} />
      <p className="mt-6 border-t border-border pt-5 text-center text-sm text-content-secondary">
        Remembered it?{' '}
        <Link to="/login" className="text-link">
          Back to sign in
        </Link>
      </p>
    </AuthShell>
  );
};

export default ResetPassword;
