import { useState } from 'react';
import { Button, Input } from '@/shared/ui';

const ExternalLink = ({ href }) => (
  <a href={href} target="_blank" rel="noopener noreferrer" className="text-link">
    {href}
  </a>
);

/**
 * The chosen fund, and its management company, editable here: it drives how
 * the engine searches, a company created earlier has none, and no other
 * screen can set one. `onSaveManager(manager)` resolves to true once saved.
 */
export const CompanyPreview = ({ company, onSaveManager, saving }) => {
  const [manager, setManager] = useState(null);

  const save = async event => {
    event.preventDefault();
    if (await onSaveManager(manager)) setManager(null);
  };

  return (
    <div className="alert alert-info mb-8">
      <h3 className="text-sm font-medium mb-2">Selected Asset Manager / Fund</h3>
      <div className="text-sm text-content">
        <p>
          <strong>{company.name}</strong>
        </p>
        {company.website_url && (
          <p className="mt-1">
            <ExternalLink href={company.website_url} />
          </p>
        )}
        {company.description && <p className="mt-1">{company.description}</p>}
      </div>

      <div className="mt-3 pt-3 border-t border-accent-blue/30">
        {manager ? (
          <form onSubmit={save} className="space-y-3">
            <Input
              label="Management company"
              value={manager.management_company_name}
              onChange={event =>
                setManager({ ...manager, management_company_name: event.target.value })
              }
              placeholder="Company running the fund"
            />
            <Input
              label="Management company website"
              type="url"
              value={manager.management_company_website}
              onChange={event =>
                setManager({ ...manager, management_company_website: event.target.value })
              }
              placeholder="https://example.com"
            />
            <div className="flex space-x-2">
              <Button type="submit" variant="primary" loading={saving}>
                Save
              </Button>
              <Button type="button" variant="secondary" onClick={() => setManager(null)}>
                Cancel
              </Button>
            </div>
          </form>
        ) : (
          <div className="flex items-start justify-between">
            <div className="text-sm text-content">
              <p className="text-xs font-medium text-accent-blue">Management company</p>
              {company.management_company_name ? (
                <>
                  <p>{company.management_company_name}</p>
                  {company.management_company_website && (
                    <ExternalLink href={company.management_company_website} />
                  )}
                </>
              ) : (
                <p className="text-content-secondary italic">
                  Not set — the engine will not be able to tell fund-level questions from
                  management-company ones.
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() =>
                setManager({
                  management_company_name: company.management_company_name || '',
                  management_company_website: company.management_company_website || '',
                })
              }
              className="text-sm text-link underline"
            >
              Edit
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
