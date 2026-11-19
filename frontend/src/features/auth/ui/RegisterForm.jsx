import { useState } from 'react';
import { AtSymbolIcon, EnvelopeIcon, LockClosedIcon, UserIcon } from '@heroicons/react/24/outline';
import { PASSWORD_RULE } from '@/entities/user';
import { useAuth } from '@/entities/viewer';
import { Button, Input, PasswordInput } from '@/shared/ui';
import { registrationProblems } from '../lib/registration';

const EMPTY = { name: '', username: '', email: '', password: '', confirmPassword: '' };

/** Create an account (always an analyst), then sign in with it. */
export const RegisterForm = () => {
  const { register } = useAuth();
  const [form, setForm] = useState(EMPTY);
  const [problems, setProblems] = useState({});
  const [loading, setLoading] = useState(false);

  const change = event => {
    const { name, value } = event.target;
    setForm(previous => ({ ...previous, [name]: value }));
    // The field's problem goes as soon as it is being corrected.
    if (problems[name]) setProblems(previous => ({ ...previous, [name]: undefined }));
  };

  const submit = async event => {
    event.preventDefault();
    const found = registrationProblems(form);
    setProblems(found);
    if (Object.keys(found).length > 0) return;
    setLoading(true);
    await register(form.name, form.username, form.email, form.password);
    setLoading(false);
  };

  const fieldProps = name => ({
    id: name,
    name,
    value: form[name],
    onChange: change,
    error: problems[name],
    required: true,
  });

  return (
    <form className="space-y-6" onSubmit={submit} noValidate>
      <div className="space-y-5">
        <Input
          {...fieldProps('name')}
          label="Full Name"
          leftIcon={UserIcon}
          autoComplete="name"
          placeholder="Jane Doe"
        />
        <Input
          {...fieldProps('username')}
          label="Username"
          leftIcon={AtSymbolIcon}
          autoComplete="username"
          placeholder="janedoe"
          helperText="Choose a unique username. You won’t be able to change it later."
        />
        <Input
          {...fieldProps('email')}
          label="Email address"
          type="email"
          leftIcon={EnvelopeIcon}
          autoComplete="email"
          placeholder="jane@example.com"
        />
        <PasswordInput
          {...fieldProps('password')}
          label="Password"
          leftIcon={LockClosedIcon}
          autoComplete="new-password"
          placeholder="••••••••"
          helperText={PASSWORD_RULE}
        />
        <PasswordInput
          {...fieldProps('confirmPassword')}
          label="Confirm Password"
          leftIcon={LockClosedIcon}
          autoComplete="new-password"
          placeholder="••••••••"
        />
      </div>

      <Button type="submit" loading={loading} variant="primary" size="lg" className="w-full">
        Create Account
      </Button>
    </form>
  );
};
