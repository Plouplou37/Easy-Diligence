import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { UserIcon, EnvelopeIcon, LockClosedIcon, EyeIcon, EyeSlashIcon, AtSymbolIcon } from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui';

// Field recipe: gradient border at rest, plain field with an error border when invalid
// (the gradient border needs its transparent border, so the two never combine).
const inputClass = (hasError, extra = '') =>
  `block w-full rounded-lg py-2 text-sm text-content pl-10 ${extra} ${
    hasError ? 'form-input border-theme-error' : 'input-gradient-border'
  }`;

const Register = () => {
  const [formData, setFormData] = useState({
    name: '',
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const { register } = useAuth();

  const validateForm = () => {
    const newErrors = {};

    if (!formData.name || formData.name.length < 2) {
      newErrors.name = 'Name must be at least 2 characters';
    }

    if (!formData.username || formData.username.length < 3) {
      newErrors.username = 'Username must be at least 3 characters';
    } else if (!/^[a-zA-Z0-9._-]+$/.test(formData.username)) {
      newErrors.username = 'Username can only contain letters, numbers, dots, hyphens, and underscores';
    } else if (formData.username.length > 30) {
      newErrors.username = 'Username must be less than 30 characters';
    }

    if (!formData.email || !/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email';
    }

    if (!formData.password || formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    } else {
      // Enhanced password validation
      if (!/(?=.*[a-z])/.test(formData.password)) {
        newErrors.password = 'Password must contain at least one lowercase letter';
      } else if (!/(?=.*[A-Z])/.test(formData.password)) {
        newErrors.password = 'Password must contain at least one uppercase letter';
      } else if (!/(?=.*\d)/.test(formData.password)) {
        newErrors.password = 'Password must contain at least one number';
      }
    }

    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) return;

    setLoading(true);
    await register(formData.name, formData.username, formData.email, formData.password);
    setLoading(false);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Clear error for this field when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  return (
    <div className="bg-auth min-h-screen overflow-y-auto flex items-center justify-center px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex flex-row w-full max-w-6xl rounded-3xl p-4 sm:p-6 gap-8 shadow-lg bg-bleu/85">
        {/* Registration card */}
        <div className="w-full lg:w-[42%] xl:w-[38%] flex justify-center">
          <div className="w-full max-w-md bg-surface shadow-xl rounded-3xl p-8 border border-border">
            <h2 className="text-center text-3xl font-bold text-content">
              Create your account
            </h2>
            <p className="mt-2 mb-8 text-center text-sm text-content-secondary">
              Or{' '}
              <Link to="/login" className="text-link">
                sign in to existing account
              </Link>
            </p>

            <form className="space-y-6" onSubmit={handleSubmit}>
              <div className="space-y-5">
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-content-secondary">
                    Full Name
                  </label>
                  <div className="mt-1 relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <UserIcon className="h-4 w-4 text-content-muted" />
                    </div>
                    <input
                      id="name"
                      name="name"
                      type="text"
                      required
                      value={formData.name}
                      onChange={handleChange}
                      className={inputClass(errors.name, 'pr-3')}
                      placeholder="John Doe"
                    />
                  </div>
                  {errors.name && (
                    <p className="mt-1 text-sm text-theme-error">{errors.name}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="username" className="block text-sm font-medium text-content-secondary">
                    Username
                  </label>
                  <div className="mt-1 relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <AtSymbolIcon className="h-4 w-4 text-content-muted" />
                    </div>
                    <input
                      id="username"
                      name="username"
                      type="text"
                      required
                      value={formData.username}
                      onChange={handleChange}
                      className={inputClass(errors.username, 'pr-3')}
                      placeholder="johndoe"
                    />
                  </div>
                  {errors.username && (
                    <p className="mt-1 text-sm text-theme-error">{errors.username}</p>
                  )}
                  <p className="mt-1 text-xs text-content-muted">
                    Choose a unique username. You won't be able to change it later.
                  </p>
                </div>

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
                      value={formData.email}
                      onChange={handleChange}
                      className={inputClass(errors.email, 'pr-3')}
                      placeholder="john@example.com"
                    />
                  </div>
                  {errors.email && (
                    <p className="mt-1 text-sm text-theme-error">{errors.email}</p>
                  )}
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
                      required
                      value={formData.password}
                      onChange={handleChange}
                      className={inputClass(errors.password, 'pr-10')}
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
                  {errors.password && (
                    <p className="mt-1 text-sm text-theme-error">{errors.password}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-content-secondary">
                    Confirm Password
                  </label>
                  <div className="mt-1 relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <LockClosedIcon className="h-4 w-4 text-content-muted" />
                    </div>
                    <input
                      id="confirmPassword"
                      name="confirmPassword"
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={formData.confirmPassword}
                      onChange={handleChange}
                      className={inputClass(errors.confirmPassword, 'pr-3')}
                      placeholder="••••••••"
                    />
                  </div>
                  {errors.confirmPassword && (
                    <p className="mt-1 text-sm text-theme-error">{errors.confirmPassword}</p>
                  )}
                </div>

                <div className="flex items-center">
                  <input
                    id="terms"
                    name="terms"
                    type="checkbox"
                    required
                    className="h-4 w-4 rounded"
                  />
                  <label htmlFor="terms" className="ml-2 block text-sm text-content-secondary">
                    I agree to the{' '}
                    <a href="#" className="text-link">
                      Terms and Conditions
                    </a>
                  </label>
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
                  Create Account
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
    </div>
  );
};

export default Register;
