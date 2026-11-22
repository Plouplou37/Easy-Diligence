import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import { displayQuestionCode } from '@/entities/dd-type';
import { Button } from '@/shared/ui';
import { StateChip, answerState, versionNote } from '@/widgets/session-workspace';

/**
 * The top of the work area: the question (code, section, text), where its
 * answer stands, and the way to the previous and next answers of the
 * questionnaire. `position` (from 1) and `total` once the order is known;
 * `onPrevious` and `onNext` are missing at either end.
 */
export const QuestionHeader = ({ answer, position, total, onPrevious, onNext }) => {
  const code = displayQuestionCode(answer.question_code);
  const note = versionNote(answer) || `Version ${answer.version || 1}`;

  return (
    <section
      aria-labelledby="answer-window-question"
      className="rounded-xl border border-border bg-surface p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-[1_1_480px]">
          <p className="text-xs text-content-muted">
            {/* The full code stays reachable on hover: it is the unique id. */}
            <span
              className="font-semibold tabular-nums text-content-secondary"
              title={answer.question_code || undefined}
            >
              {code || '—'}
            </span>
            {answer.section_name && <> · {answer.section_name}</>}
          </p>
          {/* whitespace-pre-line: imported questions carry their instructions
              on their own lines (Level, Topic, Applies to...). */}
          <h1
            id="answer-window-question"
            className="mt-1 whitespace-pre-line text-lg font-semibold leading-snug text-content"
          >
            {answer.question_text || 'Question'}
          </h1>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <StateChip state={answerState(answer)} />
            <span className="text-xs text-content-muted">{note}</span>
          </div>
        </div>

        <nav aria-label="Answers of the questionnaire" className="flex shrink-0 items-center gap-2">
          <Button
            variant="secondary"
            icon={ChevronLeftIcon}
            onClick={onPrevious}
            disabled={!onPrevious}
          >
            Previous
          </Button>
          {position > 0 && (
            <span className="px-1 text-sm text-content-muted tabular-nums">
              {position} of {total}
            </span>
          )}
          <Button variant="secondary" onClick={onNext} disabled={!onNext}>
            Next
            <ChevronRightIcon className="h-4 w-4 shrink-0" />
          </Button>
        </nav>
      </div>
    </section>
  );
};
