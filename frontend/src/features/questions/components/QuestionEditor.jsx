import React from 'react';
import { Button, field, modalStyles } from '../../../components/ui';

const QuestionEditor = ({
  question,
  onChange,
  onSave,
  onCancel
}) => {
  if (!question) return null;

  return (
    <div className={modalStyles.overlay}>
      <div className={`${modalStyles.panel} max-w-3xl max-h-[90vh] overflow-y-auto`}>
        <div className={modalStyles.header}>
          <h3 className={modalStyles.title}>
            {question.id ? 'Edit Question' : 'Create Question'}
          </h3>
        </div>

        <div className={`${modalStyles.body} space-y-4`}>
          <div>
            <label className={field.label}>
              Question Text *
            </label>
            <textarea
              value={question.question_text}
              onChange={(e) => onChange({ ...question, question_text: e.target.value })}
              placeholder="Enter the question text..."
              rows={3}
              className="form-input w-full"
              required
            />
            <p className={field.help}>
              Question code will be automatically generated
            </p>
          </div>

          <div>
            <label className={field.label}>
              Sources potentielles / Où chercher
            </label>
            <textarea
              value={question.context_prompt || ''}
              onChange={(e) => onChange({ ...question, context_prompt: e.target.value })}
              placeholder="Prospectus ; Factsheets ; DDQ ; site du gérant..."
              rows={3}
              className="form-input w-full"
            />
            <p className={field.help}>
              Transmis au modèle avec la question, sous « Where to look ».
              Modifiable à tout moment.
            </p>
          </div>
        </div>

        <div className={modalStyles.footer}>
          <Button
            onClick={onCancel}
            variant="secondary"
          >
            Cancel
          </Button>
          <Button
            onClick={onSave}
            variant="primary"
          >
            {question.id ? 'Update' : 'Create'} Question
          </Button>
        </div>
      </div>
    </div>
  );
};

export default QuestionEditor;
