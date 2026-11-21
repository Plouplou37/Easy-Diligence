import { Bars3Icon, PencilIcon, SparklesIcon, TrashIcon } from '@heroicons/react/24/outline';
import { displayQuestionCode } from '@/entities/dd-type';
import { Button } from '@/shared/ui';

/** One question of a section: its code, its text, where to look, its actions. */
const QuestionItem = ({
  question,
  sectionId,
  isValidated,
  onEdit,
  onDelete,
  dragHandlers,
  dragOverQuestion,
}) => {
  const code = displayQuestionCode(question.question_code);
  return (
    <li
      onDragOver={e => {
        e.stopPropagation();
        !isValidated && dragHandlers.onDragOver(e, question, sectionId);
      }}
      onDragLeave={e => {
        e.stopPropagation();
        dragHandlers.onDragLeave();
      }}
      onDrop={e => {
        e.stopPropagation();
        !isValidated && dragHandlers.onDrop(e, question, sectionId);
      }}
      className={`rounded-lg border transition-colors ${
        dragOverQuestion === question.id
          ? 'border-accent-blue bg-primary-dark'
          : 'border-border bg-surface-bg hover:border-border-hover'
      }`}
    >
      <div className="flex items-start gap-1 py-1.5 pl-1.5 pr-1.5 sm:gap-2">
        {!isValidated && (
          <div
            draggable
            onDragStart={e => dragHandlers.onDragStart(e, question, sectionId)}
            className="mt-0.5 shrink-0 cursor-grab rounded-md p-2 text-content-muted transition-colors hover:bg-surface-hover hover:text-content active:cursor-grabbing"
            title="Drag to reorder within the section"
          >
            <Bars3Icon className="h-4 w-4" aria-hidden="true" />
          </div>
        )}
        {/* The full code stays reachable on hover: it is the unique id. */}
        <span
          className={`w-12 shrink-0 pt-2.5 text-xs font-semibold tabular-nums text-content-secondary ${
            isValidated ? 'pl-2.5' : ''
          }`}
          title={`${question.question_code} · order ${question.order_index}`}
        >
          {code}
        </span>
        <div className="min-w-0 flex-1 py-2">
          {/* whitespace-pre-line: instructions are stored on their own lines
              and HTML would otherwise collapse them into a single block. */}
          <p className="whitespace-pre-line text-sm text-content">{question.question_text}</p>
          {question.context_prompt && (
            <div className="mt-2 border-l-2 border-theme-ai-border pl-3">
              <p className="flex items-center gap-1 text-xs font-semibold text-theme-ai">
                <SparklesIcon className="h-3 w-3 shrink-0" aria-hidden="true" />
                Where to look
              </p>
              <p className="mt-0.5 whitespace-pre-line text-xs text-content-secondary">
                {question.context_prompt}
              </p>
            </div>
          )}
        </div>

        {!isValidated && (
          <div className="flex shrink-0 items-center">
            <Button
              onClick={() => onEdit(question)}
              variant="ghost"
              size="lg"
              icon={PencilIcon}
              title="Edit question"
              aria-label={`Edit question ${code}`}
            />
            <Button
              onClick={() => onDelete(question.id)}
              variant="danger"
              size="lg"
              icon={TrashIcon}
              title="Delete question"
              aria-label={`Delete question ${code}`}
            />
          </div>
        )}
      </div>
    </li>
  );
};

export default QuestionItem;
