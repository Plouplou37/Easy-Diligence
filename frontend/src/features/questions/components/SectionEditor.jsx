import React from 'react';
import Modal from '../../../components/Modal';
import { Button, field } from '../../../components/ui';

const SectionEditor = ({ show, section, onChange, onSave, onCancel }) => {
  if (!show || !section) return null;

  return (
    <Modal
      isOpen={show}
      onClose={onCancel}
      title={section.id ? 'Edit Section' : 'Create Section'}
    >
      <div className="space-y-4">
        <div>
          <label className={field.label}>
            Title *
          </label>
          <input
            type="text"
            value={section.title || ''}
            onChange={(e) => onChange({ ...section, title: e.target.value })}
            placeholder="e.g., Company Overview"
            className="form-input w-full"
            required
          />
        </div>

        <div>
          <label className={field.label}>
            Contexte de la section
          </label>
          <textarea
            value={section.description || ''}
            onChange={(e) => onChange({ ...section, description: e.target.value })}
            placeholder="Ce que couvre ce thème, à préciser au modèle..."
            rows={3}
            className="form-input w-full"
          />
          <p className={field.help}>
            Facultatif. Transmis au modèle avec chaque question de la section.
          </p>
        </div>

        <div className="flex justify-end space-x-2 pt-4 border-t border-border">
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
            {section.id ? 'Update' : 'Create'} Section
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default SectionEditor;
