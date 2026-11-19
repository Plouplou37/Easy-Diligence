import { Link } from 'react-router-dom';
import { AuthShell, LoginForm } from '@/features/auth';

const Login = () => (
  <AuthShell
    title="Sign in to your account"
    subtitle={
      <>
        Or{' '}
        <Link to="/register" className="text-link">
          create a new account
        </Link>
      </>
    }
  >
    <LoginForm />
  </AuthShell>
);

export default Login;
