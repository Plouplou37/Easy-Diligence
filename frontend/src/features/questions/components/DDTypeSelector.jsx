import React from 'react';
import { CheckCircleIcon, TrashIcon } from '@heroicons/react/24/outline';
import { Button, Badge, field, panel } from '../../../components/ui';

const DDTypeSelector = ({ ddTypes, selectedCode, onChange, onValidate, onDelete, selectedDdType }) => {
  return (
    <div className={`${panel.base} p-6`}>
      <div className="flex items-center justify-between">
        <div className="flex-1 mr-4">
          <label className={field.label}>
            Select DD Type
          </label>
          <select
            value={selectedCode || ''}
            onChange={(e) => onChange(e.target.value)}
            className="form-input w-full py-2 text-sm"
          >
            <option value="">Select a DD Type...</option>
            {ddTypes.map((ddType) => (
              <option key={ddType.code} value={ddType.code}>
                {ddType.name}
                {ddType.is_validated ? ' - Validated' : ''}
              </option>
            ))}
          </select>
        </div>

        {selectedDdType && (
          <div className="flex items-center space-x-2">
            {!selectedDdType.is_validated && (
              <>
                <Button
                  onClick={onValidate}
                  variant="success"
                  icon={CheckCircleIcon}
                >
                  Validate
                </Button>
                <Button
                  onClick={onDelete}
                  variant="danger"
                  icon={TrashIcon}
                >
                  Delete
                </Button>
              </>
            )}
            {selectedDdType.is_validated && (
              <Badge variant="success" icon={CheckCircleIcon} size="lg">
                Validated
              </Badge>
            )}
          </div>
        )}
      </div>

      {selectedDdType && (
        <div className="mt-4 p-4 bg-surface-bg rounded-md">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-content-secondary">Sections:</span>
              <span className="ml-2 font-medium text-content">
                {selectedDdType.sections?.length || 0}
              </span>
            </div>
            <div>
              <span className="text-content-secondary">Questions:</span>
              <span className="ml-2 font-medium text-content">
                {selectedDdType.sections?.reduce((sum, s) => sum + (s.questions?.length || 0), 0) || 0}
              </span>
            </div>
            <div>
              <span className="text-content-secondary">Status:</span>
              <span className={`ml-2 font-medium ${
                selectedDdType.is_validated
                  ? 'text-theme-success'
                  : 'text-theme-warning'
              }`}>
                {selectedDdType.is_validated ? 'Validated' : 'Draft'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DDTypeSelector;
