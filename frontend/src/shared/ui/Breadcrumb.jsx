import { Link } from 'react-router-dom';
import { ChevronRightIcon, HomeIcon } from '@heroicons/react/24/outline';

const Breadcrumb = ({ items }) => {
  return (
    <nav className="flex mb-4" aria-label="Breadcrumb">
      <ol className="inline-flex flex-wrap items-center gap-1.5">
        <li className="inline-flex items-center">
          <Link
            to="/"
            className="eyebrow inline-flex items-center gap-1.5 hover:text-accent-blue transition-colors"
          >
            <HomeIcon className="w-3.5 h-3.5" />
            Dashboard
          </Link>
        </li>
        {items.map((item, index) => (
          <li key={index} className="inline-flex items-center gap-1.5">
            <ChevronRightIcon className="w-3 h-3 text-content-muted" />
            {item.href ? (
              <Link
                to={item.href}
                className="eyebrow hover:text-accent-blue transition-colors"
              >
                {item.label}
              </Link>
            ) : (
              <span className="eyebrow text-content">
                {item.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
};

export default Breadcrumb;
