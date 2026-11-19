import { downloadBlob } from '@/shared/lib/format';
import { parseSourcesFromString, getSourceContent } from './sources';

/**
 * Escapes a value for CSV format by:
 * - Converting to string
 * - Replacing double quotes with two double quotes
 * - Wrapping in double quotes
 */
export const escapeCSVValue = (value) => {
  if (value === null || value === undefined) {
    return '';
  }
  const stringValue = String(value);
  return `"${stringValue.replace(/"/g, '""')}"`;
};

/**
 * Formats sources data for CSV export
 * Handles sources that can be string, object, or array
 * Returns a human-readable string of all sources
 */
export const formatSourcesForCSV = (sources) => {
  if (!sources) {
    return '';
  }

  // Parse sources using the existing parser
  const parsedSources = parseSourcesFromString(sources);

  if (!parsedSources || parsedSources.length === 0) {
    return '';
  }

  // Extract content from each source and join with semicolons
  const sourceContents = parsedSources
    .map(source => {
      const content = getSourceContent(source);
      if (!content) return null;

      // Add source type prefix for clarity
      const typePrefix = source.type ? `[${source.type}] ` : '';
      return `${typePrefix}${content}`;
    })
    .filter(content => content !== null);

  return sourceContents.join('; ');
};

/**
 * Exports answers to CSV format
 * @param {Array} answers - Array of answer objects
 * @param {string} sessionId - Session ID for filename
 * @returns {void} - Triggers browser download
 */
export const exportAnswersToCSV = (answers, sessionId) => {
  const headers = [
    escapeCSVValue('Section'),
    escapeCSVValue('Question Text'),
    escapeCSVValue('Answer'),
    escapeCSVValue('Sources')
  ];

  const rows = answers.map(answer => [
    escapeCSVValue(answer.section_name || ''),
    escapeCSVValue(answer.question_text || ''),
    escapeCSVValue(answer.text || ''),
    escapeCSVValue(formatSourcesForCSV(answer.sources))
  ]);

  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n');

  // The byte order mark tells Excel the file is UTF-8: without it, Excel reads
  // it in the system code page and garbles every accented letter.
  const blob = new Blob(['﻿', csvContent], { type: 'text/csv;charset=utf-8;' });
  downloadBlob(blob, `session-${sessionId}-answers.csv`);
};
