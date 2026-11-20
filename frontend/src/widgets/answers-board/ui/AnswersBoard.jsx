import { useState } from 'react';
import toast from 'react-hot-toast';
import { FolderIcon } from '@heroicons/react/24/outline';
import { answersAPI } from '@/entities/answer';
import {
  AnswerCard,
  RegenerateModal,
  useAnswerEditor,
  useVersionHistory,
} from '@/features/answer-review';
import { StatTile, emptyState, panel } from '@/shared/ui';
import AnswerFilters from './AnswerFilters';
import SectionGroup from './SectionGroup';

const toggled = key => previous => ({ ...previous, [key]: !previous[key] });

/**
 * A DD type's answers to review, by section: the figures, the filters, and
 * each answer with its edit, versions and regeneration. `filters` comes from
 * useAnswerFilters (the page shares it with the CSV export); `reload` fetches
 * the answers again, without unmounting the board.
 */
const AnswersBoard = ({ filters, updateAnswer, reload }) => {
  const [expandedSections, setExpandedSections] = useState({});
  const [expandedAnswers, setExpandedAnswers] = useState({});
  const [regenerateTarget, setRegenerateTarget] = useState(null);
  const [regeneratingId, setRegeneratingId] = useState(null);
  const history = useVersionHistory();
  const editor = useAnswerEditor(updateAnswer, history.fetchVersionHistory);
  const { filtered, grouped } = filters;

  const toggleStatus = async answer => {
    try {
      await updateAnswer(answer.id, {
        status: answer.status === 'approved' ? 'needs_review' : 'approved',
      });
    } catch {
      toast.error('Failed to update the answer status');
    }
  };

  // The modal gathers the optional guidance; the call happens on submit.
  const regenerate = async ({ instruction, referenceUrl, file }) => {
    const answerId = regenerateTarget;
    if (!answerId) return;
    setRegeneratingId(answerId);
    try {
      await answersAPI.regenerate(answerId, { instruction, referenceUrl, file });
      await reload();
      setRegenerateTarget(null);
      toast.success('Answer regenerated.');
    } catch {
      toast.error('Regeneration failed. Please try again.');
    } finally {
      setRegeneratingId(null);
    }
  };

  const renderAnswer = answer => (
    <AnswerCard
      key={answer.id}
      answer={answer}
      isExpanded={expandedAnswers[answer.id]}
      onToggle={() => setExpandedAnswers(toggled(answer.id))}
      editor={editor}
      history={history}
      onRevert={(answerId, version) => history.revertToVersion(answerId, version, reload)}
      onStatusToggle={() => toggleStatus(answer)}
      onRegenerate={() => setRegenerateTarget(answer.id)}
      isRegenerating={regeneratingId === answer.id}
    />
  );

  return (
    <>
      {/* "To review" = every current answer not yet approved: a freshly
          generated answer is stored as `completed`, not `needs_review`. */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 mb-6">
        <StatTile label="Answers" value={filtered.length} />
        <StatTile
          label="To review"
          value={
            filtered.filter(answer => answer.status !== 'approved' && answer.status !== 'failed')
              .length
          }
        />
        <StatTile
          label="Approved"
          value={filtered.filter(answer => answer.status === 'approved').length}
        />
        <StatTile
          label="Edited"
          value={filtered.filter(answer => answer.version > 1).length}
          hint={`${grouped.size} sections`}
        />
      </div>

      <AnswerFilters filters={filters} />

      <div className="space-y-6 pb-12">
        {grouped.size === 0 ? (
          <div className={`${panel.base} ${emptyState.wrapper}`}>
            <FolderIcon className={emptyState.icon} />
            <h3 className={emptyState.title}>No answers found</h3>
            <p className={emptyState.text}>Try adjusting your filters or search terms.</p>
          </div>
        ) : (
          [...grouped].map(([sectionName, answers]) => (
            <SectionGroup
              key={sectionName}
              sectionName={sectionName}
              answers={answers}
              isExpanded={expandedSections[sectionName]}
              onToggle={() => setExpandedSections(toggled(sectionName))}
              renderAnswer={renderAnswer}
            />
          ))
        )}
      </div>

      <RegenerateModal
        isOpen={regenerateTarget !== null}
        onClose={() => setRegenerateTarget(null)}
        onSubmit={regenerate}
        loading={regeneratingId !== null}
      />
    </>
  );
};

export default AnswersBoard;
