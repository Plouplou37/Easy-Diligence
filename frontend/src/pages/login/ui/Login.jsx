import { AuthShell, LoginForm } from '@/features/auth';

// No self-registration: an administrator creates the accounts (Users).
const Login = () => (
  <AuthShell title="Sign in" subtitle="Your account is created by an administrator.">
    <LoginForm />
  </AuthShell>
);

export default Login;
