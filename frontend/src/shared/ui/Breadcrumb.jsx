import { Link } from 'react-router-dom';

const Breadcrumb = ({ items }) => {
  return (
    <nav className="flex mb-2" aria-label="Breadcrumb">
      <ol className="inline-flex flex-wrap items-center gap-1.5 text-sm text-content-muted">
        <li className="inline-flex items-center">
          <Link to="/" className="text-content-secondary hover:text-content transition-colors">
            Due diligences
          </Link>
        </li>
        {items.map((item, index) => (
          <li key={index} className="inline-flex items-center gap-1.5">
            <span aria-hidden="true">/</span>
            {item.href ? (
              <Link
                to={item.href}
                className="text-content-secondary hover:text-content transition-colors"
              >
                {item.label}
              </Link>
            ) : (
              <span className="text-content-muted" aria-current="page">
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
