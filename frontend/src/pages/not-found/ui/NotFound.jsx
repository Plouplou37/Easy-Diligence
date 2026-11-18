import { Link } from 'react-router-dom';
import { MapIcon } from '@heroicons/react/24/outline';
import { EmptyState, pageLayout } from '@/shared/ui';

const NotFound = () => (
  <div className={pageLayout.container}>
    <EmptyState
      icon={MapIcon}
      title="Page not found"
      text="This address does not lead anywhere in Easy Diligence."
      action={
        <Link to="/" className="text-accent-blue hover:underline">
          Back to the dashboard
        </Link>
      }
    />
  </div>
);

export default NotFound;
