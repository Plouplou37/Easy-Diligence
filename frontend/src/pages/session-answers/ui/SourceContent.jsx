import React from 'react';
import { getSourceContent } from '@/entities/answer';

/**
 * One source, as a link when it points somewhere.
 *
 * This used to live inside AnswerReview and reach only the editing view, so in
 * reading mode -- where sources are actually consulted -- every web source was
 * rendered as inert text. On a due diligence report the sources are the audit
 * trail: they have to be reachable.
 */
const SourceContent = ({ source }) => {
  const content = getSourceContent(source);
  if (content === null) {
    return null;
  }

  const isLink =
    source.type === 'web' ||
    source.type === 'web_search' ||
    (source.url && source.url.startsWith('http'));

  if (isLink) {
    const url = source.url || source.content;
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-link hover:underline break-all"
      >
        {source.title || url}
      </a>
    );
  }

  return <span className="break-all">{content}</span>;
};

export default SourceContent;
