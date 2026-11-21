import { useState } from 'react';
import { Button, Input, Modal, field, modalStyles } from '@/shared/ui';

const EMPTY = { name: '', description: '', expires_after_days: 30 };

/**
 * A new document collection (an OpenAI vector store). `onCreate(values)`
 * resolves to true once created.
 */
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
    <Modal isOpen={isOpen} onClose={close} title="New document collection">
      <form onSubmit={submit}>
        <p className="mb-5 text-sm text-content-secondary">
          A collection holds the documents of a fund or of a review. Once it exists, you add its
          files: the AI searches them for every question of the due diligences that use it.
        </p>
        <div className="space-y-5">
          <Input
            label="Name"
            required
            value={form.name}
            onChange={event => setForm({ ...form, name: event.target.value })}
            placeholder="Example Asia Fund — 2025 documents"
          />
          <div>
            <label htmlFor="vector-store-description" className={field.label}>
              Description <span className="font-normal text-content-muted">(optional)</span>
            </label>
            <textarea
              id="vector-store-description"
              value={form.description}
              onChange={event => setForm({ ...form, description: event.target.value })}
              className="form-input w-full px-3 py-2 text-sm"
              rows={3}
              aria-describedby="vector-store-description-note"
            />
            <p id="vector-store-description-note" className={field.help}>
              For your team: not sent to the AI.
            </p>
          </div>
          <Input
            label="Expires after (days without use)"
            type="number"
            min="1"
            max="365"
            required
            value={form.expires_after_days}
            onChange={event => setForm({ ...form, expires_after_days: Number(event.target.value) })}
            helperText="OpenAI deletes the collection and its documents after this many days without use: from 1 to 365."
          />
        </div>
        <div className={`${modalStyles.footer} -mx-5 -mb-4 mt-6`}>
          <Button type="button" onClick={close} variant="secondary">
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={saving}>
            Create collection
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default CreateVectorStoreModal;
