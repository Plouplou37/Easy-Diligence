import { useMemo, useState } from 'react';
import { useDebounce } from '@/shared/lib/hooks';

const UNCATEGORIZED = 'Uncategorized';

/**
 * The search and the section filter over a DD type's answers, applied here:
 * the answers are all loaded, so filtering costs no request. `filtered` feeds
 * the board and the CSV export alike.
 */
export const useAnswerFilters = answers => {
  const [searchTerm, setSearchTerm] = useState('');
  const [section, setSection] = useState('');
  const search = useDebounce(searchTerm, 300).toLowerCase();

  const sections = useMemo(
    () => [...new Set(answers.map(answer => answer.section_name).filter(Boolean))],
    [answers]
  );

  const filtered = useMemo(
    () =>
      answers.filter(
        answer =>
          (!section || answer.section_name === section) &&
          (!search ||
            answer.question_text?.toLowerCase().includes(search) ||
            answer.text?.toLowerCase().includes(search))
      ),
    [answers, section, search]
  );

  // Section name -> its answers, in the order the answers come.
  const grouped = useMemo(() => {
    const groups = new Map();
    filtered.forEach(answer => {
      const name = answer.section_name || UNCATEGORIZED;
      if (!groups.has(name)) groups.set(name, []);
      groups.get(name).push(answer);
    });
    return groups;
  }, [filtered]);

  return { searchTerm, setSearchTerm, section, setSection, sections, filtered, grouped };
};
