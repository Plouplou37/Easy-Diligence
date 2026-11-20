import { AuthShell, LoginForm } from '@/features/auth';

// No self-registration: an administrator creates the accounts (User Management).
const Login = () => (
  <AuthShell
    title="Sign in to your account"
    subtitle="Your account is created by an administrator."
  >
    <LoginForm />
  </AuthShell>
);

export default Login;
