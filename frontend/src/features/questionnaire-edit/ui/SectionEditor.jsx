import { Button, Input, Modal, field, modalStyles } from '@/shared/ui';

/** Create or edit a section: its title, and the theme told to the model. */
const SectionEditor = ({ show, section, onChange, onSave, onCancel }) => {
  if (!show || !section) return null;

  const submit = (event) => {
    event.preventDefault();
    onSave();
  };

  return (
    <Modal isOpen onClose={onCancel} title={section.id ? 'Edit Section' : 'Create Section'}>
      <form onSubmit={submit} className="space-y-4">
        <Input
          label="Title"
          required
          value={section.title || ''}
          onChange={(event) => onChange({ ...section, title: event.target.value })}
          placeholder="e.g., Company Overview"
        />

        <div>
          <label htmlFor="section-description" className={field.label}>
            Contexte de la section
          </label>
          <textarea
            id="section-description"
            value={section.description || ''}
            onChange={(event) => onChange({ ...section, description: event.target.value })}
            placeholder="Ce que couvre ce thème, à préciser au modèle..."
            rows={3}
            className="form-input w-full px-3 py-2 text-sm"
          />
          <p className={field.help}>Facultatif. Transmis au modèle avec chaque question de la section.</p>
        </div>

        <div className={`${modalStyles.footer} -mx-5 -mb-4 mt-4`}>
          <Button type="button" onClick={onCancel} variant="secondary">
            Cancel
          </Button>
          <Button type="submit" variant="primary">
            {section.id ? 'Update' : 'Create'} Section
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default SectionEditor;
