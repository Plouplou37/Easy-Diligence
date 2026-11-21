import { useState } from 'react';
import {
  Bars3Icon,
  ChevronRightIcon,
  PencilIcon,
  PlusIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { Button } from '@/shared/ui';
import QuestionItem from './QuestionItem';

// A section code is a letter or a few (services/question_codes.py); anything
// else (an older code) stays in the tooltip only.
const SHOWN_CODE = /^[A-Z]{1,3}$/;

/**
 * One section of the questionnaire, an item of its list: the title, the
 * context sent to the model, the questions once opened, and the actions.
 */
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
  dragOverQuestion,
}) => {
  const [expanded, setExpanded] = useState(false);
  const count = section.questions?.length || 0;
  const questionsId = `section-${section.id}-questions`;

  return (
    <li
      onDragOver={e => !isValidated && dragHandlers.onDragOver(e, section)}
      onDragLeave={dragHandlers.onDragLeave}
      onDrop={e => !isValidated && dragHandlers.onDrop(e, section)}
      className={`transition-colors ${
        dragOverSection === section.id
          ? 'bg-primary-dark outline-2 -outline-offset-2 outline-accent-blue'
          : ''
      }`}
    >
      <div className="flex flex-wrap items-start gap-x-2 gap-y-2 px-3 py-3 sm:px-4">
        <div className="flex min-w-0 flex-[1_1_18rem] items-start gap-1">
          {!isValidated && (
            <div
              draggable
              onDragStart={e => dragHandlers.onDragStart(e, section)}
              className="mt-0.5 shrink-0 cursor-grab rounded-md p-2 text-content-muted transition-colors hover:bg-surface-hover hover:text-content active:cursor-grabbing"
              title="Drag to reorder the sections"
            >
              <Bars3Icon className="h-4 w-4" aria-hidden="true" />
            </div>
          )}
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
            aria-controls={questionsId}
            className="flex min-h-10 min-w-0 flex-1 items-start gap-2 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-surface-hover"
          >
            <ChevronRightIcon
              className={`mt-0.5 h-4 w-4 shrink-0 text-content-muted transition-transform ${
                expanded ? 'rotate-90' : ''
              }`}
              aria-hidden="true"
            />
            <span className="min-w-0 flex-1">
              <span className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                <span
                  className="font-semibold text-content"
                  title={`Code: ${section.section_code}`}
                >
                  {SHOWN_CODE.test(section.section_code || '') && `${section.section_code}. `}
                  {section.title}
                </span>
                <span className="text-xs tabular-nums text-content-muted">
                  {count} question{count === 1 ? '' : 's'}
                </span>
              </span>
              {/* The description reaches the model with the section heading, so
                  it has to be visible: a field that is sent but never shown is
                  a field nobody can check. */}
              {section.description && (
                <span className="mt-1 block whitespace-pre-line text-sm text-content-secondary">
                  {section.description}
                </span>
              )}
            </span>
          </button>
        </div>

        {!isValidated && (
          <div className="ml-auto flex shrink-0 items-center">
            <Button
              onClick={() => onCreateQuestion(section.id)}
              variant="secondary"
              icon={PlusIcon}
              className="mr-1"
            >
              Question
            </Button>
            <Button
              onClick={() => onEditSection(section)}
              variant="ghost"
              size="lg"
              icon={PencilIcon}
              title="Edit section"
              aria-label={`Edit the section ${section.title}`}
            />
            <Button
              onClick={() => onDeleteSection(section.id)}
              variant="danger"
              size="lg"
              icon={TrashIcon}
              title="Delete section"
              aria-label={`Delete the section ${section.title}`}
            />
          </div>
        )}
      </div>

      {expanded && (
        <div id={questionsId} className="px-3 pb-4 sm:pl-14 sm:pr-4">
          {count > 0 ? (
            <ol className="space-y-2">
              {[...section.questions]
                .sort((a, b) => a.order_index - b.order_index)
                .map(question => (
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
                ))}
            </ol>
          ) : (
            <div className="rounded-lg border border-dashed border-border-hover px-4 py-6 text-center">
              <p className="text-sm text-content-muted">No questions in this section yet.</p>
              {!isValidated && (
                <Button
                  onClick={() => onCreateQuestion(section.id)}
                  variant="secondary"
                  icon={PlusIcon}
                  className="mt-3"
                >
                  Add the first question
                </Button>
              )}
            </div>
          )}
        </div>
      )}
    </li>
  );
};

export default SectionCard;
