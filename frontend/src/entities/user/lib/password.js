/** What the backend requires of a password (core/validation.py), said up front. */
export const PASSWORD_RULE =
  'At least 8 characters, with an uppercase letter, a lowercase letter and a digit.';

/**
 * Why `password` would be refused, or null. Mirrors validate_password_strength
 * in backend/app/core/validation.py, so the form answers before the request.
 */
export const passwordProblem = password => {
  if (!password || password.length < 8) return 'Password must be at least 8 characters long';
  if (new TextEncoder().encode(password).length > 72)
    return 'Password must be at most 72 bytes long';
  if (!/[A-Z]/.test(password)) return 'Password must contain at least one uppercase letter';
  if (!/[a-z]/.test(password)) return 'Password must contain at least one lowercase letter';
  if (!/\d/.test(password)) return 'Password must contain at least one digit';
  return null;
};
