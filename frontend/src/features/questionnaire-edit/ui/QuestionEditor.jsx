import { displayQuestionCode } from '@/entities/dd-type';
import { AiBadge, Button, FieldLabel, Modal, field, modalStyles } from '@/shared/ui';

/**
 * Create or edit a question: its text, and where the model should look.
 * `sectionTitle`: the title of its section, shown for context.
 */
const QuestionEditor = ({ question, sectionTitle, onChange, onSave, onCancel }) => {
  if (!question) return null;

  const submit = event => {
    event.preventDefault();
    onSave();
  };

  const code = question.id ? displayQuestionCode(question.question_code) : null;

  return (
    <Modal
      isOpen
      onClose={onCancel}
      title={question.id ? `Edit question ${code || ''}`.trim() : 'New question'}
      size="lg"
    >
      <form onSubmit={submit}>
        <p className="mb-5 text-sm text-content-secondary">
          {sectionTitle ? (
            <>
              In the section <span className="font-medium text-content">{sectionTitle}</span>.{' '}
            </>
          ) : null}
          The model reads the question with its section’s title and context, then the hint on where
          to look.
        </p>

        <div className="space-y-5">
          <div>
            <FieldLabel htmlFor="question-text" required aside={<AiBadge />}>
              Question
            </FieldLabel>
            <textarea
              id="question-text"
              value={question.question_text}
              onChange={event => onChange({ ...question, question_text: event.target.value })}
              placeholder="When was the fund launched, and how large is it today?"
              rows={3}
              className="form-input w-full px-3 py-2 text-sm"
              required
              aria-describedby={question.id ? undefined : 'question-text-note'}
            />
            {!question.id && (
              <p id="question-text-note" className={field.help}>
                Its code (A.01…) is given automatically.
              </p>
            )}
          </div>

          <div>
            <FieldLabel htmlFor="question-context" aside={<AiBadge />}>
              Where to look <span className="font-normal text-content-muted">(optional)</span>
            </FieldLabel>
            <textarea
              id="question-context"
              value={question.context_prompt || ''}
              onChange={event => onChange({ ...question, context_prompt: event.target.value })}
              placeholder="Latest factsheet or annual report. Give the launch date, then the assets under management with their date."
              rows={3}
              className="form-input w-full px-3 py-2 text-sm"
              aria-describedby="question-context-note"
            />
            <p id="question-context-note" className={field.help}>
              The documents or sources to search first, and what the answer should give. Sent with
              the question, after “Where to look:”. It can change until the questionnaire is
              validated.
            </p>
          </div>
        </div>

        <div className={`${modalStyles.footer} -mx-5 -mb-4 mt-6`}>
          <Button type="button" onClick={onCancel} variant="secondary">
            Cancel
          </Button>
          <Button type="submit" variant="primary">
            {question.id ? 'Save question' : 'Add question'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default QuestionEditor;
