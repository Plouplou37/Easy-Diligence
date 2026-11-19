import { useState } from 'react';
import { BuildingOfficeIcon } from '@heroicons/react/24/outline';
import { Button, field } from '@/shared/ui';
import { NewCompanyForm } from './NewCompanyForm';

/**
 * Choose the fund of the session, among the existing ones or a new one.
 * `companies`: useCompanies. `companyId`: the chosen one's id, or ''.
 */
export const CompanyPicker = ({ companies, companyId, onSelect }) => {
  const [creating, setCreating] = useState(false);

  const create = async (values) => {
    const company = await companies.create(values);
    if (company) {
      onSelect(company.id);
      setCreating(false);
    }
    return company;
  };

  return (
    <>
      {companies.companies.length > 0 && (
        <div className="mb-4">
          <label htmlFor="company" className={field.label}>
            Existing Asset Manager / Fund
          </label>
          <select
            id="company"
            value={companyId}
            onChange={(event) => {
              onSelect(event.target.value ? Number(event.target.value) : '');
              setCreating(false);
            }}
            className="form-input mt-1 block w-full pl-3 pr-10 py-2 text-base"
          >
            <option value="">Select an asset manager or fund...</option>
            {companies.companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="flex items-center mb-4">
        <div className="flex-1 border-t border-border"></div>
        <span className="mx-4 eyebrow">OR</span>
        <div className="flex-1 border-t border-border"></div>
      </div>

      <Button
        variant="secondary"
        onClick={() => {
          if (!creating) onSelect('');
          setCreating(!creating);
        }}
        icon={BuildingOfficeIcon}
        aria-expanded={creating}
      >
        {creating ? 'Cancel' : 'Create New Asset Manager / Fund'}
      </Button>

      {creating && <NewCompanyForm onCreate={create} saving={companies.saving} />}
    </>
  );
};
