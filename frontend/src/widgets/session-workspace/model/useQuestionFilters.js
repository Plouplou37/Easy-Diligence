import { useMemo, useState } from 'react';
import { useDebounce } from '@/shared/lib/hooks';
import { STATE_ORDER } from '../lib/questionnaire';

/**
 * The section, the status and the search over a questionnaire's questions,
 * applied here: they are all loaded, so filtering costs no request. `counts`
 * are those of each status within the section and the search, so the status
 * filter says what it would show.
 */
export const useQuestionFilters = rows => {
  const [section, setSection] = useState('');
  const [state, setState] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const search = useDebounce(searchTerm, 200).trim().toLowerCase();

  const searched = useMemo(
    () =>
      rows.filter(
        row =>
          (!section || row.sectionKey === section) && (!search || row.haystack.includes(search))
      ),
    [rows, section, search]
  );

  const counts = useMemo(() => {
    const result = Object.fromEntries(STATE_ORDER.map(key => [key, 0]));
    searched.forEach(row => {
      result[row.state] += 1;
    });
    return { ...result, all: searched.length };
  }, [searched]);

  const filtered = useMemo(
    () => (state ? searched.filter(row => row.state === state) : searched),
    [searched, state]
  );

  return {
    section,
    setSection,
    state,
    setState,
    searchTerm,
    setSearchTerm,
    counts,
    filtered,
    active: Boolean(section || state || search),
  };
};
