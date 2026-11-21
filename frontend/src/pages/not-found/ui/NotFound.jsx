import { useNavigate } from 'react-router-dom';
import { ArrowLeftIcon, MapIcon } from '@heroicons/react/24/outline';
import { Button, pageLayout, panel } from '@/shared/ui';

const NotFound = () => {
  const navigate = useNavigate();
  return (
    <div className={pageLayout.container}>
      <div className={`${panel.base} mx-auto mt-8 max-w-lg px-6 py-12 text-center sm:px-10`}>
        <MapIcon className="mx-auto h-10 w-10 text-content-muted" aria-hidden="true" />
        <p className="eyebrow mt-4">Error 404</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-content">Page not found</h1>
        <p className="mt-2 text-sm text-content-secondary">
          This address does not lead anywhere in Easy Diligence. The link may be old, or the page
          may have moved.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-2">
          <Button variant="secondary" icon={ArrowLeftIcon} onClick={() => navigate(-1)}>
            Go back
          </Button>
          <Button variant="primary" onClick={() => navigate('/')}>
            Go to the due diligences
          </Button>
        </div>
      </div>
    </div>
  );
};

export default NotFound;
