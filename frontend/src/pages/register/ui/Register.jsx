import { Link } from 'react-router-dom';
import { AuthShell, RegisterForm } from '@/features/auth';

const Register = () => (
  <AuthShell
    title="Create your account"
    subtitle={
      <>
        Or{' '}
        <Link to="/login" className="text-link">
          sign in to an existing account
        </Link>
      </>
    }
  >
    <RegisterForm />
  </AuthShell>
);

export default Register;
