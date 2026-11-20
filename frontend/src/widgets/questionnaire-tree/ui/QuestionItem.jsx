import { DocumentTextIcon, PencilIcon, TrashIcon, Bars3Icon } from '@heroicons/react/24/outline';
import { Button } from '@/shared/ui';
import { displayQuestionCode } from '@/entities/dd-type';

const QuestionItem = ({
  question,
  sectionId,
  isValidated,
  onEdit,
  onDelete,
  dragHandlers,
  dragOverQuestion,
}) => {
  return (
    <div
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
      className={`p-3 border rounded-md bg-surface-bg ${
        dragOverQuestion === question.id
          ? 'border-accent-blue border-2 bg-accent-blue/10!'
          : 'border-border hover:bg-surface-hover'
      } transition-colors`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1">
          {!isValidated && (
            <div
              draggable
              onDragStart={e => dragHandlers.onDragStart(e, question, sectionId)}
              className="cursor-move p-1 hover:bg-surface-hover rounded-sm mt-0.5"
            >
              <Bars3Icon className="h-4 w-4 text-content-muted" />
            </div>
          )}
          <DocumentTextIcon className="h-5 w-5 text-content-muted mt-0.5 shrink-0" />
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              {/* The full code stays reachable on hover: it is the unique id. */}
              <span
                className="font-mono text-xs bg-surface-hover text-content-secondary px-2 py-0.5 rounded-sm"
                title={`${question.question_code} · order ${question.order_index}`}
              >
                {displayQuestionCode(question.question_code)}
              </span>
            </div>
            {/* whitespace-pre-line: instructions are stored on their own lines
                and HTML would otherwise collapse them into a single block. */}
            <p className="mt-1 text-sm text-content whitespace-pre-line">
              {question.question_text}
            </p>
            {question.context_prompt && (
              <p className="mt-1 text-xs text-content-muted italic whitespace-pre-line">
                Sources : {question.context_prompt}
              </p>
            )}
          </div>
        </div>

        {!isValidated && (
          <div className="flex items-center space-x-1 ml-2">
            <Button
              onClick={() => onEdit(question)}
              variant="ghost"
              size="sm"
              icon={PencilIcon}
              title="Edit question"
            />
            <Button
              onClick={() => onDelete(question.id)}
              variant="danger"
              size="sm"
              icon={TrashIcon}
              title="Delete question"
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default QuestionItem;
