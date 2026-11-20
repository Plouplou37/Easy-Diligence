import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useDdTypes } from '@/entities/dd-type';
import { sessionAPI } from '@/entities/session';
import {
  CompanyPicker,
  CompanyPreview,
  DdTypePicker,
  useCompanies,
} from '@/features/session-create';
import { errorMessage } from '@/shared/api';
import { Button, Input, PageHeader, field, pageLayout, panel, sectionHeader } from '@/shared/ui';

const Section = ({ title, children }) => (
  <div className="mb-8">
    <div className={`${sectionHeader.wrapper} mb-4`}>
      <h2 className={sectionHeader.title}>{title}</h2>
      <div className={sectionHeader.hairline} />
    </div>
    {children}
  </div>
);

const SessionCreate = () => {
  const navigate = useNavigate();
  const companies = useCompanies();
  const { ddTypes } = useDdTypes();
  const [companyId, setCompanyId] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  // null until the user changes it: every active DD type, by default.
  const [chosenCodes, setChosenCodes] = useState(null);
  const [creating, setCreating] = useState(false);

  const codes = chosenCodes ?? ddTypes.map(ddType => ddType.code);
  const company = companies.companies.find(item => item.id === companyId);
  const ready = Boolean(companyId) && Boolean(name.trim()) && codes.length > 0;

  const create = async () => {
    setCreating(true);
    try {
      const response = await sessionAPI.create({
        company_id: companyId,
        name,
        description,
        dd_type_ids: ddTypes.filter(ddType => codes.includes(ddType.code)).map(ddType => ddType.id),
      });
      toast.success('Session created successfully');
      navigate(`/session/${response.data.session_code || response.data.id}`, {
        state: { newSession: true },
      });
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to create session'));
      setCreating(false);
    }
  };

  return (
    <div className={`${pageLayout.container} h-full flex flex-col`}>
      <div className="shrink-0">
        <PageHeader
          breadcrumb={[{ label: 'New Session' }]}
          title="Create New DD Session"
          subtitle="Choose the fund, name the session and pick the due diligence types to run"
        />
      </div>

      <div className={`${panel.base} flex-1 min-h-0 overflow-y-auto`}>
        <div className="px-6 py-8">
          <Section title="Select Asset Manager / Fund">
            <CompanyPicker companies={companies} companyId={companyId} onSelect={setCompanyId} />
          </Section>

          <Section title="Session Details">
            <div className="grid grid-cols-1 gap-4">
              <Input
                label="Session Name"
                required
                value={name}
                onChange={event => setName(event.target.value)}
                placeholder="e.g., Q4 Due Diligence"
              />
              <div>
                <label htmlFor="session-description" className={field.label}>
                  Description
                </label>
                <textarea
                  id="session-description"
                  value={description}
                  onChange={event => setDescription(event.target.value)}
                  rows={3}
                  className="form-input mt-1 block w-full px-3 py-2 text-sm"
                  placeholder="Describe the purpose and scope of this DD session"
                />
              </div>
            </div>
          </Section>

          <Section title="Due Diligence Types">
            <p className="text-sm text-content-secondary -mt-2 mb-6">
              Select which types of due diligence analysis to include in this session.
            </p>
            <DdTypePicker ddTypes={ddTypes} selected={codes} onChange={setChosenCodes} />
          </Section>

          {/* Keyed by company: a half-typed manager never moves to another one. */}
          {company && (
            <CompanyPreview
              key={company.id}
              company={company}
              saving={companies.saving}
              onSaveManager={manager => companies.saveManager(company, manager)}
            />
          )}

          <div className="flex justify-end space-x-3">
            <Button variant="secondary" onClick={() => navigate('/')}>
              Cancel
            </Button>
            <Button variant="primary" onClick={create} disabled={!ready} loading={creating}>
              Create Session
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SessionCreate;
