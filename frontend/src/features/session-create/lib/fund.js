// The fund under review and its management company, as models/company.py
// stores them. Every one of these fields reaches the model
// (services/processing.build_company_info).
export const EMPTY_FUND = {
  name: '',
  website_url: '',
  description: '',
  management_company_name: '',
  management_company_website: '',
};

const FUND_FIELDS = Object.keys(EMPTY_FUND);

// The column sizes of models/company.py: a longer value would be refused.
export const FUND_LIMITS = {
  name: 255,
  website_url: 500,
  management_company_name: 255,
  management_company_website: 500,
};

/** The fields of a stored company, as the form edits them ('' when missing). */
export const fieldsOf = company =>
  Object.fromEntries(FUND_FIELDS.map(key => [key, company?.[key] ?? '']));

/** The fields as the API stores them: trimmed, null when empty. */
export const toPayload = fields =>
  Object.fromEntries(FUND_FIELDS.map(key => [key, (fields[key] || '').trim() || null]));

export const sameFields = (a, b) =>
  FUND_FIELDS.every(key => (a?.[key] || '').trim() === (b?.[key] || '').trim());

/**
 * What blocks step 1, keyed by the id of the field to fix (the first one gets
 * the focus). `fund`: useFundDraft. `details`: the due diligence's own name
 * and description.
 */
export const fundStepErrors = (fund, details) => {
  const errors = {};
  if (fund.mode === 'existing') {
    if (!fund.company) errors['fund-company'] = 'Choose a fund, or add a new one.';
    else if (fund.dirty) errors['fund-save'] = 'Save your changes to this fund, or cancel them.';
  } else if (fund.mode === 'new') {
    if (!fund.newFields.name.trim()) {
      errors['fund-name'] = "Give the fund's name: the AI reads it before every question.";
    }
  } else {
    errors['fund-company'] = 'The funds are still loading.';
  }
  if (!details.name.trim()) {
    errors['dd-name'] = 'Name this due diligence, so your team can find it.';
  }
  return errors;
};
