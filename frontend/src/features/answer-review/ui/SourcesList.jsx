import {
  DocumentIcon,
  LinkIcon,
  ArrowDownTrayIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import { parseSourcesFromString, getSourceContent } from '@/entities/answer';
import SourceContent from './SourceContent';

const SourcesList = ({ sources: rawSources, compact = false }) => {
  // Check if sources are already parsed (array) or need parsing (string/object)
  const sources = Array.isArray(rawSources) ? rawSources : parseSourcesFromString(rawSources);

  const getIcon = type => {
    const sizeClass = compact ? 'w-3 h-3' : 'w-4 h-4';
    switch (type) {
      case 'file':
        return <DocumentIcon className={`${sizeClass} mr-1 text-accent-green`} />;
      case 'file_search':
        return <DocumentIcon className={`${sizeClass} mr-1 text-accent-green`} />;
      case 'web':
        return <LinkIcon className={`${sizeClass} mr-1 text-accent-blue`} />;
      case 'web_search':
        return <MagnifyingGlassIcon className={`${sizeClass} mr-1 text-accent-blue`} />;
      default:
        return <ArrowDownTrayIcon className={`${sizeClass} mr-1 text-content-muted`} />;
    }
  };

  const getTypeLabel = type => {
    switch (type) {
      case 'file':
        return 'Files';
      case 'file_search':
        return 'Vector Store Search';
      case 'web':
        return 'Web URLs';
      case 'web_search':
        return 'Web Searches';
      default:
        return 'Other Sources';
    }
  };

  if (!sources || sources.length === 0) {
    return (
      <div className={`${compact ? 'p-2' : 'p-3'} bg-surface-bg rounded-md`}>
        <p className="text-xs text-content-secondary">No source information available</p>
      </div>
    );
  }

  const groupedSources = sources.reduce((acc, source) => {
    const type = source.type || 'other';
    if (!acc[type]) acc[type] = [];
    acc[type].push(source);
    return acc;
  }, {});

  return (
    <div className={compact ? 'text-xs space-y-2' : 'text-sm space-y-3'}>
      {Object.entries(groupedSources).map(([type, typeSources]) => {
        const validSources = typeSources.filter(source => getSourceContent(source));

        if (validSources.length === 0) return null;

        return (
          <div key={type}>
            <div className="flex items-center mb-2">
              {getIcon(type)}
              <span
                className={`${compact ? 'text-xs' : 'text-sm'} font-medium text-content-secondary`}
              >
                {getTypeLabel(type)} ({validSources.length})
              </span>
            </div>
            <div className={`${compact ? 'ml-4' : 'ml-5'} space-y-1`}>
              {validSources.map((source, idx) => (
                <p key={idx} className="text-xs text-content-secondary break-words">
                  <SourceContent source={source} />
                </p>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default SourcesList;
