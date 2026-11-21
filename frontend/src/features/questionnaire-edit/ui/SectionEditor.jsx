import { AiBadge, Button, FieldLabel, Input, Modal, field, modalStyles } from '@/shared/ui';

/** Create or edit a section: its title, and the theme told to the model. */
const SectionEditor = ({ show, section, onChange, onSave, onCancel }) => {
  if (!show || !section) return null;

  const submit = event => {
    event.preventDefault();
    onSave();
  };

  return (
    <Modal isOpen onClose={onCancel} title={section.id ? 'Edit section' : 'New section'}>
      <form onSubmit={submit}>
        <p className="mb-5 text-sm text-content-secondary">
          The model reads the section’s title and context with each of its questions.
        </p>

        <div className="space-y-5">
          <div>
            <FieldLabel htmlFor="section-title" required aside={<AiBadge />}>
              Title
            </FieldLabel>
            <Input
              id="section-title"
              required
              value={section.title || ''}
              onChange={event => onChange({ ...section, title: event.target.value })}
              placeholder="Fund identity"
            />
          </div>

          <div>
            <FieldLabel htmlFor="section-description" aside={<AiBadge />}>
              Section context <span className="font-normal text-content-muted">(optional)</span>
            </FieldLabel>
            <textarea
              id="section-description"
              value={section.description || ''}
              onChange={event => onChange({ ...section, description: event.target.value })}
              placeholder="What this theme covers, for the model"
              rows={3}
              className="form-input w-full px-3 py-2 text-sm"
              aria-describedby="section-description-note"
            />
            <p id="section-description-note" className={field.help}>
              Sent with every question of the section, under its title.
            </p>
          </div>
        </div>

        <div className={`${modalStyles.footer} -mx-5 -mb-4 mt-6`}>
          <Button type="button" onClick={onCancel} variant="secondary">
            Cancel
          </Button>
          <Button type="submit" variant="primary">
            {section.id ? 'Save section' : 'Add section'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default SectionEditor;
