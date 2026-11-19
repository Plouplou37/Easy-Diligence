import { useState } from 'react';
import {
  FolderIcon,
  PencilIcon,
  TrashIcon,
  PlusIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  Bars3Icon
} from '@heroicons/react/24/outline';
import { Button } from '@/shared/ui';
import QuestionItem from './QuestionItem';

const SectionCard = ({
  section,
  isValidated,
  onEditSection,
  onDeleteSection,
  onCreateQuestion,
  onEditQuestion,
  onDeleteQuestion,
  dragHandlers,
  questionDragHandlers,
  dragOverSection,
  dragOverQuestion
}) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      onDragOver={(e) => !isValidated && dragHandlers.onDragOver(e, section)}
      onDragLeave={dragHandlers.onDragLeave}
      onDrop={(e) => !isValidated && dragHandlers.onDrop(e, section)}
      className={`relative bg-surface rounded-lg shadow-sm ${
        dragOverSection === section.id
          ? 'border-2 border-accent-blue'
          : 'border border-border'
      }`}
    >
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3 flex-1">
            {!isValidated && (
              <div
                draggable
                onDragStart={(e) => dragHandlers.onDragStart(e, section)}
                className="cursor-move p-1 hover:bg-surface-hover rounded"
              >
                <Bars3Icon className="h-5 w-5 text-content-muted" />
              </div>
            )}
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="text-content-muted hover:text-content"
              aria-expanded={expanded}
              aria-label={`${expanded ? 'Hide' : 'Show'} the questions of ${section.title}`}
            >
              {expanded ? (
                <ChevronDownIcon className="h-5 w-5" />
              ) : (
                <ChevronRightIcon className="h-5 w-5" />
              )}
            </button>
            <FolderIcon className="h-5 w-5 text-accent-blue" />
            <div>
              <h3 className="text-fluid-md font-medium text-content" title={`Code: ${section.section_code}`}>
                {section.title}
              </h3>
              <p className="text-sm text-content-muted">
                {section.questions?.length || 0} questions
              </p>
              {/* The description reaches the model with the section heading, so
                  it has to be visible: a field that is sent but never shown is
                  a field nobody can check. */}
              {section.description && (
                <p className="mt-1 text-sm text-content-secondary whitespace-pre-line">
                  {section.description}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Button
              onClick={() => onCreateQuestion(section.id)}
              disabled={isValidated}
              variant="primary"
              size="sm"
              icon={PlusIcon}
            >
              Question
            </Button>
            {!isValidated && (
              <>
                <Button
                  onClick={() => onEditSection(section)}
                  variant="ghost"
                  size="sm"
                  icon={PencilIcon}
                />
                <Button
                  onClick={() => onDeleteSection(section.id)}
                  variant="danger"
                  size="sm"
                  icon={TrashIcon}
                />
              </>
            )}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="p-4 space-y-2">
          {section.questions && section.questions.length > 0 ? (
            [...section.questions]
              .sort((a, b) => a.order_index - b.order_index)
              .map((question) => (
              <QuestionItem
                key={question.id}
                question={question}
                sectionId={section.id}
                isValidated={isValidated}
                onEdit={onEditQuestion}
                onDelete={onDeleteQuestion}
                dragHandlers={questionDragHandlers}
                dragOverQuestion={dragOverQuestion}
              />
            ))
          ) : (
            <div className="text-center py-8 text-content-muted">
              <p className="text-sm">No questions in this section</p>
              {!isValidated && (
                <div className="mt-2">
                  <Button
                    onClick={() => onCreateQuestion(section.id)}
                    variant="ghost"
                    size="sm"
                  >
                    Add your first question
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SectionCard;
