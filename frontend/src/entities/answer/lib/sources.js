// Helper function to deduplicate sources by unique identifier
const deduplicateSources = sources => {
  const seen = new Map();

  sources.forEach(source => {
    let key;

    // Determine unique key based on source type
    if (source.type === 'file_search' || source.type === 'file') {
      key = source.filename || source.file_id || source.content;
    } else if (source.type === 'web_search' || source.type === 'web') {
      key = source.url || source.content;
    } else {
      key = JSON.stringify(source); // Fallback for unknown types
    }

    // Only keep first occurrence of each unique source
    if (key && !seen.has(key)) {
      seen.set(key, source);
    }
  });

  return Array.from(seen.values());
};

export const parseSourcesFromString = sourcesData => {
  if (!sourcesData) return [];

  let parsed;

  if (typeof sourcesData === 'string') {
    try {
      parsed = JSON.parse(sourcesData);
    } catch (error) {
      return [{ type: 'file', content: sourcesData, filename: sourcesData }];
    }
  } else if (typeof sourcesData === 'object') {
    parsed = sourcesData;
  } else {
    return [];
  }

  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
    const allSources = [];

    if (Array.isArray(parsed.files)) {
      allSources.push(
        ...parsed.files.map(source => ({
          ...source,
          type: source.type || 'file',
        }))
      );
    }

    if (Array.isArray(parsed.web)) {
      allSources.push(
        ...parsed.web.map(source => ({
          ...source,
          type: source.type || 'web',
        }))
      );
    }

    if (Array.isArray(parsed.webUrls)) {
      allSources.push(
        ...parsed.webUrls.map(source => ({
          ...source,
          type: source.type || 'web',
        }))
      );
    }

    if (Array.isArray(parsed.webSearchQueries)) {
      allSources.push(
        ...parsed.webSearchQueries.map(source => ({
          ...source,
          type: source.type || 'web_search',
        }))
      );
    }

    if (allSources.length === 0 && Object.keys(parsed).length === 0) {
      return [{ type: 'unknown', content: 'Sources data unavailable', filename: 'Unknown source' }];
    }

    // Deduplicate sources by unique key (filename for files, URL for web)
    return deduplicateSources(allSources);
  }

  if (Array.isArray(parsed)) {
    const processedSources = parsed.map(source => {
      if (typeof source === 'string') {
        if (source.startsWith('http')) {
          return { type: 'web', content: source, url: source };
        } else if (source.includes('web_search:')) {
          return {
            type: 'web_search',
            content: source.replace('web_search:', ''),
            query: source.replace('web_search:', ''),
          };
        } else {
          return { type: 'file', content: source, filename: source };
        }
      } else if (source && typeof source === 'object') {
        if (source.type === 'file_search') {
          return {
            ...source,
            type: 'file_search',
            content: source.queries ? source.queries.join(', ') : 'File search performed',
            filenames: source.filenames || [],
          };
        }
        return { ...source, type: source.type || (source.url ? 'web' : 'file') };
      }
      return source;
    });

    return deduplicateSources(processedSources);
  }

  if (parsed && typeof parsed === 'object') {
    let singleSource;
    if (parsed.type === 'file_search') {
      singleSource = {
        ...parsed,
        type: 'file_search',
        content: parsed.queries ? parsed.queries.join(', ') : 'File search performed',
        filenames: parsed.filenames || [],
      };
    } else {
      singleSource = {
        ...parsed,
        type: parsed.type || (parsed.url ? 'web' : 'file'),
      };
    }
    return [singleSource];
  }

  return [];
};

export const getSourceContent = source => {
  if (source.type === 'file_search') {
    // Each file citation is a separate source with single filename
    if (source.filename) {
      return source.filename;
    }
    // Don't show file_search without actual filename
    return null;
  }

  if (source.type === 'web_search') {
    // For web searches, only show URL if available, not query
    if (source.url) {
      return source.url;
    }
    // Don't show web search queries without URLs
    return null;
  }

  // For other types, show URL, filename, or content
  return source.url || source.filename || source.content || null;
};
