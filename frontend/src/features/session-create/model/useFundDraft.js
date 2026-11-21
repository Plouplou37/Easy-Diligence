import { useState } from 'react';
import { EMPTY_FUND, fieldsOf, sameFields } from '../lib/fund';

/**
 * The fund of the new due diligence: one already in Easy Diligence, whose
 * details can be edited and saved here, or a new one, added only when the due
 * diligence is created. `companies`: useCompanies.
 *
 * `fields` are the details as the AI would read them now, unsaved edits
 * included, for the preview.
 */
export const useFundDraft = companies => {
  // null until the user picks: an existing fund when there are some.
  const [chosenMode, setChosenMode] = useState(null);
  const [companyId, setCompanyId] = useState('');
  const [newFields, setNewFields] = useState(EMPTY_FUND);
  // The existing fund's details while they are edited, null otherwise.
  const [editFields, setEditFields] = useState(null);

  const list = companies.companies;
  let mode = chosenMode;
  if (!mode && !companies.loading) mode = list.length > 0 ? 'existing' : 'new';

  const company = list.find(item => item.id === companyId) || null;
  const editing = mode === 'existing' && Boolean(company) && editFields !== null;
  const dirty = editing && !sameFields(editFields, fieldsOf(company));

  let fields = fieldsOf(company);
  if (mode === 'new') fields = newFields;
  else if (editing) fields = editFields;

  const adopt = created => {
    setChosenMode('existing');
    setCompanyId(created.id);
    setEditFields(null);
  };

  return {
    mode,
    company,
    companyId,
    newFields,
    editFields,
    editing,
    dirty,
    fields,
    setMode: setChosenMode,
    choose: id => {
      setChosenMode('existing');
      setCompanyId(id);
      setEditFields(null);
    },
    setNewField: (key, value) => {
      setChosenMode('new');
      setNewFields(previous => ({ ...previous, [key]: value }));
    },
    startEdit: () => setEditFields(fieldsOf(company)),
    setEditField: (key, value) => setEditFields(previous => ({ ...previous, [key]: value })),
    cancelEdit: () => setEditFields(null),
    /** Resolves to true once the edited details are saved. */
    saveEdit: async () => {
      const saved = await companies.save(company, editFields);
      if (saved) setEditFields(null);
      return Boolean(saved);
    },
    /**
     * Add the new fund. Resolves to it, or null. The draft then points at it,
     * so trying again after a later failure does not add it twice.
     */
    createNew: async () => {
      const created = await companies.create(newFields);
      if (created) adopt(created);
      return created;
    },
  };
};
