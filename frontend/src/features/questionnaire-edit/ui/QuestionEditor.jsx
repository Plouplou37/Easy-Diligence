import { Button, Modal, field, modalStyles } from '@/shared/ui';

/** Create or edit a question: its text, and where the model should look. */
const QuestionEditor = ({ question, onChange, onSave, onCancel }) => {
  if (!question) return null;

  const submit = (event) => {
    event.preventDefault();
    onSave();
  };

  return (
    <Modal isOpen onClose={onCancel} title={question.id ? 'Edit Question' : 'Create Question'} size="lg">
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label htmlFor="question-text" className={field.label}>
            Question Text <span className="text-theme-error">*</span>
          </label>
          <textarea
            id="question-text"
            value={question.question_text}
            onChange={(event) => onChange({ ...question, question_text: event.target.value })}
            placeholder="Enter the question text..."
            rows={3}
            className="form-input w-full px-3 py-2 text-sm"
            required
          />
          {!question.id && <p className={field.help}>The question code is given automatically.</p>}
        </div>

        <div>
          <label htmlFor="question-context" className={field.label}>
            Sources potentielles / Où chercher
          </label>
          <textarea
            id="question-context"
            value={question.context_prompt || ''}
            onChange={(event) => onChange({ ...question, context_prompt: event.target.value })}
            placeholder="Prospectus ; Factsheets ; DDQ ; site du gérant..."
            rows={3}
            className="form-input w-full px-3 py-2 text-sm"
          />
          <p className={field.help}>
            Transmis au modèle avec la question, sous « Where to look ». Modifiable à tout moment.
          </p>
        </div>

        <div className={`${modalStyles.footer} -mx-5 -mb-4 mt-4`}>
          <Button type="button" onClick={onCancel} variant="secondary">
            Cancel
          </Button>
          <Button type="submit" variant="primary">
            {question.id ? 'Update' : 'Create'} Question
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default QuestionEditor;
