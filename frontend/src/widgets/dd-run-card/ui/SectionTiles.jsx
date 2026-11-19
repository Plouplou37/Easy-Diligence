import { useEffect, useState } from 'react';
import { fetchDdTypes } from '@/entities/dd-type';
import { FINISHED_STATUSES } from '@/entities/execution';

// Translucent tones, so the counters drawn over the fill stay readable in both themes.
const fillOf = (section, percentage) => {
  if (section.status === 'completed') return 'bg-theme-success/40';
  if (section.status === 'in_progress') return 'bg-accent-blue/40 animate-pulse';
  if (percentage > 0) return 'bg-theme-warning/40';
  return 'bg-content-muted/40';
};

/** One tile per section: answered / total, and the share filled. */
export const SectionTiles = ({ sections, neutral = false }) => (
  <div className="flex space-x-1 overflow-x-auto pb-1 custom-scrollbar">
    {sections.map((section, index) => {
      const done = section.questions_completed || 0;
      const total = section.total_questions || 0;
      const percentage = total > 0 ? Math.round((done / total) * 100) : 0;
      return (
        <div
          key={index}
          className="relative h-6 flex-1 min-w-[90px] rounded-md overflow-hidden"
          title={`${section.name || `Section ${index + 1}`}: ${done}/${total} questions (${percentage}%)`}
        >
          <div className="absolute inset-0 bg-surface-hover" />
          <div
            className={`absolute inset-y-0 left-0 rounded-md transition-all duration-300 ${
              neutral ? 'bg-content-muted/40' : fillOf(section, percentage)
            }`}
            style={{ width: `${percentage}%` }}
          />
          <div className="absolute inset-0 flex items-center justify-between px-2 gap-2">
            <span className="text-[10px] font-medium text-content whitespace-nowrap tabular-nums">
              {done}/{total}
            </span>
            <span className="text-[10px] font-bold text-content tabular-nums">{percentage}%</span>
          </div>
        </div>
      );
    })}
  </div>
);

/**
 * Before any progress is known: the DD type's own sections, from its
 * structure (shared by every card of the page: one request for all).
 */
export const StructureTiles = ({ ddTypeCode, parentStatus }) => {
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(true);
  // "Could not load" is not "no sections".
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!ddTypeCode) return;
    const finished = FINISHED_STATUSES.includes(parentStatus);
    fetchDdTypes({ withQuestions: true })
      .then((ddTypes) => {
        const matched = ddTypes.find((ddType) => ddType.code === ddTypeCode);
        if (!matched) {
          setFailed(true);
          return;
        }
        setSections(
          (matched.sections || []).map((section) => {
            const total = section.questions?.length || 0;
            return {
              name: section.title,
              total_questions: total,
              questions_completed: finished ? total : 0,
              status: finished ? 'completed' : 'not_started',
            };
          })
        );
      })
      .catch(() => setFailed(true))
      .finally(() => setLoading(false));
    // On the code and the status, not the objects: the session page rebuilds
    // its progress on every poll.
  }, [ddTypeCode, parentStatus]);

  if (loading) {
    return (
      <div className="flex space-x-1">
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="h-6 flex-1 rounded-md bg-surface-hover animate-pulse" />
        ))}
      </div>
    );
  }
  if (sections.length === 0) {
    return (
      <div className="h-6 flex items-center rounded-md bg-surface-bg px-2">
        <span className="text-[11px] text-content-muted">
          {failed ? 'Sections unavailable — reload the page' : 'No section in this DD type'}
        </span>
      </div>
    );
  }
  return <SectionTiles sections={sections} neutral />;
};
