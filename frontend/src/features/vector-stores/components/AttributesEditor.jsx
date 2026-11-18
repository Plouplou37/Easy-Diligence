import React from 'react';
import { PlusIcon, TrashIcon, XMarkIcon } from '@heroicons/react/24/outline';
import Modal from '../../../components/Modal';
import { Button } from '../../../components/ui';

const AttributesEditor = ({ show, file, attributes, onAdd, onChange, onRemove, onSave, onCancel }) => {
  if (!show) return null;

  return (
    <Modal isOpen={show} onClose={onCancel} title={`Edit Attributes - ${file?.filename}`}>
      <div className="space-y-4">
        <p className="text-sm text-content-secondary">
          Add metadata attributes to help categorize and filter this file.
        </p>

        <div className="space-y-2 max-h-96 overflow-y-auto p-0.5">
          {Object.entries(attributes).map(([key, value]) => (
            <div key={key} className="flex gap-2">
              <input
                type="text"
                value={key}
                onChange={(e) => onChange(key, e.target.value, value)}
                placeholder="Key"
                className="form-input flex-1"
              />
              <input
                type="text"
                value={value}
                onChange={(e) => onChange(key, key, e.target.value)}
                placeholder="Value"
                className="form-input flex-1"
              />
              <button
                onClick={() => onRemove(key)}
                className="p-2 text-theme-error hover:opacity-80"
              >
                <TrashIcon className="h-5 w-5" />
              </button>
            </div>
          ))}
        </div>

        <button
          onClick={onAdd}
          className="w-full px-3 py-2 border-2 border-dashed border-border rounded-md text-sm text-content-secondary hover:border-accent-blue hover:text-accent-blue transition-colors flex items-center justify-center gap-2"
        >
          <PlusIcon className="h-4 w-4" />
          Add Attribute
        </button>

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
            Save Attributes
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default AttributesEditor;
