import { useState } from 'react';
import { Button, Input, field } from '@/shared/ui';

const EMPTY = {
  name: '',
  website_url: '',
  description: '',
  // Named apart from the fund: the engine tells the model which entity a
  // question is about, which drives how it searches.
  management_company_name: '',
  management_company_website: '',
};

/** A new fund and its management company. `onCreate(values)` resolves to the company or null. */
export const NewCompanyForm = ({ onCreate, saving }) => {
  const [form, setForm] = useState(EMPTY);
  const set = name => event => setForm(previous => ({ ...previous, [name]: event.target.value }));

  const submit = async event => {
    event.preventDefault();
    if (await onCreate(form)) setForm(EMPTY);
  };

  return (
    <form onSubmit={submit} className="mt-6 form-surface p-4">
      <h3 className="text-base font-medium text-content mb-4">New Asset Manager / Fund Details</h3>
      <div className="grid grid-cols-1 gap-4">
        <Input
          label="Fund / product under review"
          required
          value={form.name}
          onChange={set('name')}
          placeholder="Exact legal name of the fund"
        />
        <Input
          label="Fund website URL"
          type="url"
          value={form.website_url}
          onChange={set('website_url')}
          placeholder="https://example.com"
        />
        <Input
          label="Management company"
          value={form.management_company_name}
          onChange={set('management_company_name')}
          placeholder="Company running the fund"
        />
        <Input
          label="Management company website"
          type="url"
          value={form.management_company_website}
          onChange={set('management_company_website')}
          placeholder="https://example.com"
        />
        <div>
          <label htmlFor="company-description" className={field.label}>
            Description
          </label>
          <textarea
            id="company-description"
            value={form.description}
            onChange={set('description')}
            rows={3}
            className="form-input mt-1 block w-full px-3 py-2 text-sm"
            placeholder="Brief description of the asset manager or fund"
          />
        </div>
        <Button
          type="submit"
          variant="primary"
          disabled={!form.name}
          loading={saving}
          className="w-full"
        >
          Create Asset Manager / Fund
        </Button>
      </div>
    </form>
  );
};
