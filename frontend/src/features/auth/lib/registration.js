import { passwordProblem } from '@/entities/user';

// The username rule of the backend (models/user.py, UserProfile).
const USERNAME = /^[a-zA-Z0-9._-]+$/;

/** The problems of a sign-up form, by field: empty when it can be sent. */
export const registrationProblems = ({ name, username, email, password, confirmPassword }) => {
  const problems = {};
  if (!name || name.trim().length < 2) problems.name = 'Name must be at least 2 characters';

  if (!username || username.length < 3) problems.username = 'Username must be at least 3 characters';
  else if (username.length > 30) problems.username = 'Username must be at most 30 characters';
  else if (!USERNAME.test(username)) {
    problems.username = 'Username can only contain letters, numbers, dots, hyphens and underscores';
  }

  if (!email || !/\S+@\S+\.\S+/.test(email)) problems.email = 'Please enter a valid email';

  const weak = passwordProblem(password);
  if (weak) problems.password = weak;
  if (password !== confirmPassword) problems.confirmPassword = 'Passwords do not match';
  return problems;
};
