import { useState } from 'react';
import { AiBadge, Button, Input, LoadingSpinner, field } from '@/shared/ui';
import { FUND_LIMITS } from '../lib/fund';
import { plural } from '../lib/text';
import { NotSentNote } from './NotSentNote';
import { ChoiceCard } from './ChoiceCard';
import { FieldError, FieldLabel, InsetBlock, TextAreaField } from './fields';

const NO_MANAGER =
  'Without it, the AI has to guess whether a question is about the fund or the company running it.';

const isWebLink = value => /^https?:\/\//i.test(value || '');

/** The fund's details as inputs. `onChange(key, value)`. */
const FundFields = ({ values, onChange, errors }) => {
  const set = key => event => onChange(key, event.target.value);
  return (
    <>
      <InsetBlock title="The fund">
        <div className="flex flex-wrap gap-4">
          <Input
            id="fund-name"
            className="flex-[1_1_15rem]"
            label={<FieldLabel text="Fund name" required badge={<AiBadge />} />}
            aria-required="true"
            maxLength={FUND_LIMITS.name}
            value={values.name}
            onChange={set('name')}
            error={errors['fund-name']}
            placeholder="Exact legal name of the fund"
            autoComplete="off"
          />
          <Input
            id="fund-website"
            className="flex-[1_1_15rem]"
            type="url"
            label={<FieldLabel text="Website" badge={<AiBadge />} />}
            maxLength={FUND_LIMITS.website_url}
            value={values.website_url}
            onChange={set('website_url')}
            placeholder="https://example.com"
            autoComplete="off"
          />
        </div>
        <TextAreaField
          id="fund-overview"
          label={<FieldLabel text="Short description" badge={<AiBadge />} />}
          rows={3}
          value={values.description}
          onChange={set('description')}
          helper="One or two sentences: the strategy and the asset class help the AI search the right things."
          placeholder="A long-only equity fund investing in listed companies across Asia"
        />
      </InsetBlock>

      <InsetBlock title="Its management company">
        <div className="flex flex-wrap gap-4">
          <Input
            id="manager-name"
            className="flex-[1_1_15rem]"
            label={<FieldLabel text="Name" badge={<AiBadge />} />}
            maxLength={FUND_LIMITS.management_company_name}
            value={values.management_company_name}
            onChange={set('management_company_name')}
            placeholder="The company running the fund"
            helperText={values.management_company_name.trim() ? undefined : NO_MANAGER}
            autoComplete="off"
          />
          <Input
            id="manager-website"
            className="flex-[1_1_15rem]"
            type="url"
            label={<FieldLabel text="Website" badge={<AiBadge />} />}
            maxLength={FUND_LIMITS.management_company_website}
            value={values.management_company_website}
            onChange={set('management_company_website')}
            placeholder="https://example.com"
            autoComplete="off"
          />
        </div>
      </InsetBlock>
    </>
  );
};

/** One detail of a stored fund, read only. */
const Detail = ({ label, value, empty, link = false, className = '' }) => {
  let shown = <p className="text-sm italic text-content-muted">{empty}</p>;
  if (value && link && isWebLink(value)) {
    shown = (
      <a
        href={value}
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm text-link break-all"
      >
        {value}
      </a>
    );
  } else if (value) {
    shown = <p className="text-sm text-content whitespace-pre-line break-words">{value}</p>;
  }
  return (
    <div className={`flex min-w-0 flex-col gap-1 ${className}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-content">{label}</span>
        <AiBadge />
      </div>
      {shown}
    </div>
  );
};

/** The details of a fund already in Easy Diligence, as the AI will read them. */
const FundSummary = ({ company, onEdit }) => (
  <>
    <InsetBlock
      title="The fund"
      aside={
        <button type="button" onClick={onEdit} className="min-h-10 px-1 text-sm text-link">
          Edit the details
        </button>
      }
    >
      <div className="flex flex-wrap gap-4">
        <Detail className="flex-[1_1_15rem]" label="Fund name" value={company.name} />
        <Detail
          className="flex-[1_1_15rem]"
          label="Website"
          value={company.website_url}
          empty="No website"
          link
        />
      </div>
      <Detail label="Short description" value={company.description} empty="No description" />
    </InsetBlock>

    <InsetBlock title="Its management company">
      <div className="flex flex-wrap gap-4">
        <Detail
          className="flex-[1_1_15rem]"
          label="Name"
          value={company.management_company_name}
          empty="Not set"
        />
        <Detail
          className="flex-[1_1_15rem]"
          label="Website"
          value={company.management_company_website}
          empty="No website"
          link
        />
      </div>
      {!company.management_company_name && (
        <p className="text-xs text-theme-warning">{NO_MANAGER}</p>
      )}
    </InsetBlock>
  </>
);

/** Pick a fund already in Easy Diligence, see its details, edit them. */
const ExistingFund = ({ companies, fund, errors }) => {
  const [nameError, setNameError] = useState(null);
  const sorted = [...companies.companies].sort((a, b) => a.name.localeCompare(b.name));
  const pickError = errors['fund-company'];

  const save = async () => {
    if (!fund.editFields.name.trim()) {
      setNameError("The fund's name cannot be empty.");
      document.getElementById('fund-name')?.focus();
      return;
    }
    setNameError(null);
    await fund.saveEdit();
  };

  return (
    <>
      <div>
        <label htmlFor="fund-company" className={field.label}>
          Fund
        </label>
        <select
          id="fund-company"
          value={fund.companyId}
          onChange={event => fund.choose(event.target.value ? Number(event.target.value) : '')}
          aria-invalid={pickError ? true : undefined}
          aria-describedby={pickError ? 'fund-company-error' : undefined}
          className={`form-input h-10 w-full ${pickError ? 'border-theme-error' : ''}`}
        >
          <option value="">Choose a fund…</option>
          {sorted.map(company => (
            <option key={company.id} value={company.id}>
              {company.name}
              {company.management_company_name ? ` — ${company.management_company_name}` : ''}
            </option>
          ))}
        </select>
        <FieldError id="fund-company-error">{pickError}</FieldError>
      </div>

      {fund.company && !fund.editing && (
        <FundSummary company={fund.company} onEdit={fund.startEdit} />
      )}

      {fund.editing && (
        <>
          <FundFields
            values={fund.editFields}
            onChange={(key, value) => {
              if (key === 'name') setNameError(null);
              fund.setEditField(key, value);
            }}
            errors={{ 'fund-name': nameError }}
          />
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="button"
                id="fund-save"
                variant="secondary"
                onClick={save}
                loading={companies.saving}
                disabled={!fund.dirty}
                aria-describedby={errors['fund-save'] ? 'fund-save-error' : undefined}
              >
                Save the details
              </Button>
              <Button type="button" variant="ghost" onClick={fund.cancelEdit}>
                Cancel
              </Button>
            </div>
            <p className={field.help}>
              Saved details apply to every due diligence on this fund, and to their next runs.
            </p>
            <FieldError id="fund-save-error">{errors['fund-save']}</FieldError>
          </div>
        </>
      )}
    </>
  );
};

/**
 * Step 1: the fund and its management company, which the AI reads before
 * every question, and the due diligence's own name and description, which it
 * never reads. `fund`: useFundDraft. `onDetailsChange(key, value)`.
 * `errors`: keyed by field id.
 */
export const FundStep = ({ companies, fund, details, onDetailsChange, errors }) => {
  if (!fund.mode) return <LoadingSpinner text="Loading the funds..." />;
  const count = companies.companies.length;

  return (
    <div className="flex flex-col gap-6">
      {count > 0 && (
        <fieldset>
          <legend className="sr-only">Which fund</legend>
          <div className="flex flex-wrap gap-3">
            <ChoiceCard
              id="fund-mode-existing"
              name="fund-mode"
              className="flex-[1_1_15rem]"
              checked={fund.mode === 'existing'}
              onChange={() => fund.setMode('existing')}
              title="A fund already in Easy Diligence"
              hint={`${plural(count, 'fund')} to choose from`}
            />
            <ChoiceCard
              id="fund-mode-new"
              name="fund-mode"
              className="flex-[1_1_15rem]"
              checked={fund.mode === 'new'}
              onChange={() => fund.setMode('new')}
              title="A new fund"
              hint="Added when you create the due diligence"
            />
          </div>
        </fieldset>
      )}

      {fund.mode === 'existing' ? (
        <ExistingFund companies={companies} fund={fund} errors={errors} />
      ) : (
        <FundFields values={fund.newFields} onChange={fund.setNewField} errors={errors} />
      )}

      <InsetBlock title="This due diligence">
        <Input
          id="dd-name"
          label={<FieldLabel text="Name" required badge={<NotSentNote />} />}
          aria-required="true"
          maxLength={255}
          value={details.name}
          onChange={event => onDetailsChange('name', event.target.value)}
          error={errors['dd-name']}
          placeholder="e.g. Example Asia Fund — annual review 2026"
          autoComplete="off"
        />
        <TextAreaField
          id="dd-description"
          label={<FieldLabel text="Description" badge={<NotSentNote />} />}
          rows={2}
          value={details.description}
          onChange={event => onDetailsChange('description', event.target.value)}
          placeholder="Its purpose and scope, for your team"
        />
      </InsetBlock>
    </div>
  );
};
