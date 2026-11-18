import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { LockClosedIcon, EnvelopeIcon, EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import { Button, modalStyles } from '../components/ui';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const { login, resetPassword } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    await login(email, password);
    setLoading(false);
  };

  const handleForgotPassword = async () => {
    if (!forgotEmail) {
      toast.error('Please enter your email address');
      return;
    }

    const result = await resetPassword(forgotEmail);
    if (result.success) {
      setShowForgotModal(false);
      setForgotEmail('');
    }
  };

  return (
    <div className="bg-auth min-h-screen overflow-y-auto flex items-center justify-center px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex flex-row w-full max-w-6xl rounded-3xl p-4 sm:p-6 gap-8 shadow-lg bg-bleu/85">
        {/* Sign-in card */}
        <div className="w-full lg:w-[42%] xl:w-[38%] flex justify-center">
          <div className="w-full max-w-md bg-surface shadow-xl rounded-3xl p-8 border border-border">
            <h2 className="text-center text-3xl font-bold text-content">
              Sign in to your account
            </h2>
            <p className="mt-2 mb-8 text-center text-sm text-content-secondary">
              Or{' '}
              <Link to="/register" className="text-link">
                create a new account
              </Link>
            </p>

            <form className="space-y-6" onSubmit={handleSubmit}>
              <div className="space-y-5">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-content-secondary">
                    Email address
                  </label>
                  <div className="mt-1 relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <EnvelopeIcon className="h-4 w-4 text-content-muted" />
                    </div>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="block w-full rounded-lg input-gradient-border pl-10 pr-3 py-2 text-sm text-content"
                      placeholder="admin@example.com"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-content-secondary">
                    Password
                  </label>
                  <div className="mt-1 relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <LockClosedIcon className="h-4 w-4 text-content-muted" />
                    </div>
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="block w-full rounded-lg input-gradient-border pl-10 pr-10 py-2 text-sm text-content"
                      placeholder="••••••••"
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-content-muted hover:text-content transition-colors"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? (
                        <EyeSlashIcon className="h-4 w-4" />
                      ) : (
                        <EyeIcon className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <input
                      id="remember-me"
                      name="remember-me"
                      type="checkbox"
                      className="h-4 w-4 rounded"
                    />
                    <label htmlFor="remember-me" className="ml-2 block text-sm text-content-secondary">
                      Remember me
                    </label>
                  </div>

                  <div className="text-sm">
                    <button
                      type="button"
                      onClick={() => setShowForgotModal(true)}
                      className="text-link"
                    >
                      Forgot your password?
                    </button>
                  </div>
                </div>
              </div>

              <div>
                <Button
                  type="submit"
                  disabled={loading}
                  loading={loading}
                  variant="primary"
                  size="lg"
                  className="w-full"
                >
                  Sign in
                </Button>
              </div>

            </form>
          </div>
        </div>

        {/* Brand panel */}
        <div className="hidden lg:flex flex-1 items-center justify-center">
          <img
            src="/logo-white.svg"
            alt="Easy Diligence"
            className="w-[80%] h-auto"
          />
        </div>
      </div>

      {/* Forgot Password Modal */}
      {showForgotModal && (
        <div className={modalStyles.overlay}>
          <div className={`${modalStyles.panel} max-w-md`}>
            <div className={modalStyles.header}>
              <h3 className={modalStyles.title}>
                Reset Password
              </h3>
            </div>

            <div className={modalStyles.body}>
              <p className="text-sm text-content-secondary mb-4">
                Enter your email address and we'll send you instructions to reset your password.
              </p>

              <label className="block text-sm font-medium text-content-secondary mb-2">
                Email Address
              </label>
              <input
                type="email"
                value={forgotEmail}
                onChange={(e) => setForgotEmail(e.target.value)}
                className="form-input w-full py-2 text-sm"
                placeholder="Enter your email address"
              />
            </div>

            <div className={modalStyles.footer}>
              <Button
                onClick={() => {
                  setShowForgotModal(false);
                  setForgotEmail('');
                }}
                variant="secondary"
              >
                Cancel
              </Button>
              <Button
                onClick={handleForgotPassword}
                variant="primary"
              >
                Send Reset Link
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Login;
