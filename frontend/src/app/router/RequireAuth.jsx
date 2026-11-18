import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/entities/viewer';
import { LoadingSpinner } from '@/shared/ui';

const FullPageSpinner = () => (
  <div className="min-h-screen flex items-center justify-center">
    <LoadingSpinner size="lg" />
  </div>
);

/** The routes inside need a logged-in user (an admin, with adminOnly). */
export const RequireAuth = ({ adminOnly = false }) => {
  const { isAuthenticated, isAdmin, loading } = useAuth();
  if (loading) return <FullPageSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (adminOnly && !isAdmin) return <Navigate to="/" replace />;
  return <Outlet />;
};

/** The routes inside are for visitors: a logged-in user goes to the dashboard. */
export const GuestOnly = () => {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <FullPageSpinner />;
  if (isAuthenticated) return <Navigate to="/" replace />;
  return <Outlet />;
};
