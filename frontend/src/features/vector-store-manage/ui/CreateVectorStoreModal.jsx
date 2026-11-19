import { useState } from 'react';
import { Button, Input, Modal, field, modalStyles } from '@/shared/ui';

const EMPTY = { name: '', description: '', expires_after_days: 30 };

/** A new vector store. `onCreate(values)` resolves to true once created. */
const CreateVectorStoreModal = ({ isOpen, onClose, onCreate }) => {
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);

  const close = () => {
    setForm(EMPTY);
    onClose();
  };

  const submit = async event => {
    event.preventDefault();
    setSaving(true);
    const created = await onCreate(form);
    setSaving(false);
    if (created) close();
  };

  return (
    <Modal isOpen={isOpen} onClose={close} title="Create New Vector Store">
      <form onSubmit={submit} className="space-y-4">
        <Input
          label="Name"
          required
          value={form.name}
          onChange={event => setForm({ ...form, name: event.target.value })}
        />
        <div>
          <label htmlFor="vector-store-description" className={field.label}>
            Description
          </label>
          <textarea
            id="vector-store-description"
            value={form.description}
            onChange={event => setForm({ ...form, description: event.target.value })}
            className="form-input w-full px-3 py-2 text-sm"
            rows={3}
          />
        </div>
        <Input
          label="Expires after (days without use)"
          type="number"
          min="1"
          max="365"
          required
          value={form.expires_after_days}
          onChange={event => setForm({ ...form, expires_after_days: Number(event.target.value) })}
        />
        <div className={`${modalStyles.footer} -mx-5 -mb-4 mt-4`}>
          <Button type="button" onClick={close} variant="secondary">
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={saving}>
            Create
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default CreateVectorStoreModal;
