import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BuildingOfficeIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  FunnelIcon
} from '@heroicons/react/24/outline';
import Layout from '../components/Layout';
import { companyAPI, sessionAPI, ddTypesAPI } from '../services/api';
import toast from 'react-hot-toast';
import {
  Button,
  EmptyState,
  Input,
  PageHeader,
  SearchInput,
  field,
  pageLayout,
  panel,
  sectionHeader,
} from '../components/ui';
import { getDdTypeIcon } from '../utils/ddTypeIcon';

const SessionCreate = () => {
  const [companies, setCompanies] = useState([]);
  const [ddTypes, setDdTypes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    company_id: '',
    name: '',
    description: '',
    dd_type_codes: [], // Will be populated with available DD type codes
    newCompany: {
      name: '',
      website_url: '',
      description: '',
      // Named apart from the fund: the engine tells the model which entity a
      // question is about, which drives how it searches.
      management_company_name: '',
      management_company_website: ''
    }
  });
  const [ddTypeSearch, setDdTypeSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [showNewCompanyForm, setShowNewCompanyForm] = useState(false);
  // Companies created before the fund / management company split have no
  // manager on record, and nothing else in the app can set one.
  const [editingManager, setEditingManager] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadCompanies();
    loadDdTypes();
  }, []);

  const loadCompanies = async () => {
    try {
      const response = await companyAPI.list();
      setCompanies(response.data);
    } catch (error) {
      toast.error('Failed to load companies');
    }
  };

  const loadDdTypes = async () => {
    try {
      const response = await ddTypesAPI.list(true);
      setDdTypes(response.data);
      setFormData(prev => ({
        ...prev,
        dd_type_codes: response.data.map(dd => dd.code)
      }));
    } catch (error) {
      toast.error('Failed to load DD types');
      setDdTypes([]);
    }
  };


  const handleCreateCompany = async () => {
    try {
      setLoading(true);
      const response = await companyAPI.create(formData.newCompany);
      setCompanies(prev => [...prev, response.data]);
      setFormData(prev => ({
        ...prev,
        company_id: response.data.id
      }));
      setShowNewCompanyForm(false);
      toast.success('Company created successfully');
    } catch (error) {
      toast.error('Failed to create company');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveManager = async (company) => {
    try {
      setLoading(true);
      // PUT /company/{id} takes a whole company, not a patch: it reassigns
      // every field it receives. Sending only the manager would blank the rest.
      const response = await companyAPI.update(company.id, {
        name: company.name,
        website_url: company.website_url,
        description: company.description,
        management_company_name: editingManager.management_company_name || null,
        management_company_website: editingManager.management_company_website || null
      });
      setCompanies(prev => prev.map(c => (c.id === company.id ? response.data : c)));
      setEditingManager(null);
      toast.success('Management company saved');
    } catch (error) {
      toast.error(
        error.response?.status === 403
          ? 'Only the owner of this company can edit it'
          : 'Failed to save management company'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSession = async () => {
    try {
      setLoading(true);

      // Convert dd_type_codes to dd_type_ids
      const ddTypeIds = formData.dd_type_codes.map(code => {
        const ddType = ddTypes.find(dd => dd.code === code);
        return ddType?.id;
      }).filter(id => id !== undefined);

      const sessionResponse = await sessionAPI.create({
        company_id: parseInt(formData.company_id),
        name: formData.name,
        description: formData.description,
        dd_type_ids: ddTypeIds
      });

      toast.success('Session created successfully');

      const sessionIdentifier = sessionResponse.data.session_code || sessionResponse.data.id;
      navigate(`/session/${sessionIdentifier}`, {
        state: { newSession: true }
      });
    } catch (error) {
      toast.error('Failed to create session');
    } finally {
      setLoading(false);
    }
  };


  const selectedCompany = companies.find(c => c.id === parseInt(formData.company_id));

  // Helper function to categorize DD types
  const categorizeDdType = (name) => {
    const nameLower = name.toLowerCase();
    if (nameLower.includes('financial') || nameLower.includes('example')) {
      return 'financial';
    }
    if (nameLower.includes('operational') || nameLower.includes('operation')) {
      return 'operational';
    }
    if (nameLower.includes('legal') || nameLower.includes('compliance') || nameLower.includes('sanity')) {
      return 'legal';
    }
    if (nameLower.includes('esg') || nameLower.includes('environmental') || nameLower.includes('sustainability')) {
      return 'esg';
    }
    if (nameLower.includes('technical') || nameLower.includes('technology') || nameLower.includes('it')) {
      return 'technical';
    }
    return 'other';
  };

  // Filter and search DD types
  const filteredDdTypes = ddTypes.filter(dd => {
    const matchesSearch = !ddTypeSearch ||
      dd.name.toLowerCase().includes(ddTypeSearch.toLowerCase()) ||
      (dd.description && dd.description.toLowerCase().includes(ddTypeSearch.toLowerCase()));

    const matchesCategory = selectedCategory === 'all' || categorizeDdType(dd.name) === selectedCategory;

    return matchesSearch && matchesCategory;
  });

  // Get available categories
  const getAvailableCategories = () => {
    const categories = ddTypes.map(dd => categorizeDdType(dd.name));
    const uniqueCategories = [...new Set(categories)];
    return uniqueCategories.map(cat => ({
      key: cat,
      label: cat.charAt(0).toUpperCase() + cat.slice(1),
      count: categories.filter(c => c === cat).length
    }));
  };

  const availableCategories = getAvailableCategories();

  return (
      <Layout>
        <div className={`${pageLayout.container} h-full flex flex-col`}>
          <div className="flex-shrink-0">
            <PageHeader
              breadcrumb={[{ label: 'New Session' }]}
              title="Create New DD Session"
              subtitle="Choose the fund, name the session and pick the due diligence types to run"
            />
          </div>

          <div className={`${panel.base} flex-1 min-h-0 overflow-y-auto`}>
            <div className="px-6 py-8">
              {/* Asset Manager/Fund Selection */}
              <div className="mb-8">
                <div className={`${sectionHeader.wrapper} mb-4`}>
                  <h2 className={sectionHeader.title}>Select Asset Manager / Fund</h2>
                  <div className={sectionHeader.hairline} />
                </div>

                {companies.length > 0 && (
                  <div className="mb-4">
                    <label className={field.label}>
                      Existing Asset Manager / Fund
                    </label>
                    <select
                      value={formData.company_id}
                      onChange={(e) => {
                        setFormData(prev => ({ ...prev, company_id: e.target.value }));
                        setShowNewCompanyForm(false);
                        // Drop any half-typed manager: it belongs to the company
                        // being left, and saving it onto the next one would be wrong.
                        setEditingManager(null);
                      }}
                      className="form-input mt-1 block w-full pl-3 pr-10 py-2 text-base"
                    >
                      <option value="">Select an asset manager or fund...</option>
                      {companies.map(company => (
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
                    setShowNewCompanyForm(!showNewCompanyForm);
                    if (!showNewCompanyForm) {
                      setFormData(prev => ({ ...prev, company_id: '' }));
                    }
                  }}
                  icon={BuildingOfficeIcon}
                >
                  {showNewCompanyForm ? 'Cancel' : 'Create New Asset Manager / Fund'}
                </Button>

                {showNewCompanyForm && (
                  <div className="mt-6 form-surface p-4">
                    <h3 className="text-base font-medium text-content mb-4">New Asset Manager / Fund Details</h3>
                    <div className="grid grid-cols-1 gap-4">
                      <Input
                        label="Fund / product under review"
                        type="text"
                        required
                        value={formData.newCompany.name}
                        onChange={(e) => setFormData(prev => ({
                          ...prev,
                          newCompany: { ...prev.newCompany, name: e.target.value }
                        }))}
                        placeholder="Exact legal name of the fund"
                      />
                      <Input
                        label="Fund website URL"
                        type="url"
                        value={formData.newCompany.website_url}
                        onChange={(e) => setFormData(prev => ({
                          ...prev,
                          newCompany: { ...prev.newCompany, website_url: e.target.value }
                        }))}
                        placeholder="https://example.com"
                      />
                      <Input
                        label="Management company"
                        type="text"
                        value={formData.newCompany.management_company_name}
                        onChange={(e) => setFormData(prev => ({
                          ...prev,
                          newCompany: { ...prev.newCompany, management_company_name: e.target.value }
                        }))}
                        placeholder="Company running the fund"
                      />
                      <Input
                        label="Management company website"
                        type="url"
                        value={formData.newCompany.management_company_website}
                        onChange={(e) => setFormData(prev => ({
                          ...prev,
                          newCompany: { ...prev.newCompany, management_company_website: e.target.value }
                        }))}
                        placeholder="https://example.com"
                      />
                      <div>
                        <label className={field.label}>
                          Description
                        </label>
                        <textarea
                          value={formData.newCompany.description}
                          onChange={(e) => setFormData(prev => ({
                            ...prev,
                            newCompany: { ...prev.newCompany, description: e.target.value }
                          }))}
                          rows={3}
                          className="form-input mt-1 block w-full px-3 py-2 text-sm"
                          placeholder="Brief description of the asset manager or fund"
                        />
                      </div>
                      <Button
                        variant="primary"
                        onClick={handleCreateCompany}
                        disabled={!formData.newCompany.name || loading}
                        loading={loading}
                        className="w-full"
                      >
                        {loading ? 'Creating...' : 'Create Asset Manager / Fund'}
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              {/* Session Details */}
              <div className="mb-8">
                <div className={`${sectionHeader.wrapper} mb-4`}>
                  <h2 className={sectionHeader.title}>Session Details</h2>
                  <div className={sectionHeader.hairline} />
                </div>
                <div className="grid grid-cols-1 gap-4">
                  <Input
                    label="Session Name"
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Q4 2024 Due Diligence"
                  />
                  <div>
                    <label className={field.label}>
                      Description
                    </label>
                    <textarea
                      value={formData.description}
                      onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                      rows={3}
                      className="form-input mt-1 block w-full px-3 py-2 text-sm"
                      placeholder="Describe the purpose and scope of this DD session"
                    />
                  </div>
                </div>
              </div>

              {/* Due Diligence Type Selection */}
              <div className="mb-8">
                <div className={`${sectionHeader.wrapper} mb-2`}>
                  <h2 className={sectionHeader.title}>Due Diligence Types</h2>
                  <div className={sectionHeader.hairline} />
                </div>
                <p className="text-sm text-content-secondary mb-6">
                  Select which types of due diligence analysis to include in this session.
                </p>

                {/* Search and Filter Controls */}
                {ddTypes.length > 6 && (
                  <div className="mb-6 space-y-4">
                    {/* Search Bar */}
                    <SearchInput
                      placeholder="Search due diligence types..."
                      value={ddTypeSearch}
                      onChange={setDdTypeSearch}
                    />

                    {/* Category Filter */}
                    {availableCategories.length > 1 && (
                      <div className="flex flex-wrap items-center gap-2">
                        <FunnelIcon className="h-4 w-4 text-content-muted" />
                        <span className="eyebrow mr-2">Filter by category:</span>
                        <button
                          onClick={() => setSelectedCategory('all')}
                          data-active={selectedCategory === 'all'}
                          className="pill-action"
                        >
                          All ({ddTypes.length})
                        </button>
                        {availableCategories.map(category => (
                          <button
                            key={category.key}
                            onClick={() => setSelectedCategory(category.key)}
                            data-active={selectedCategory === category.key}
                            className="pill-action"
                          >
                            {category.label} ({category.count})
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Selection Summary */}
                <div className="mb-4 flex items-center justify-between">
                  <div className="text-sm text-content-secondary">
                    {formData.dd_type_codes.length > 0 ? (
                      <span>{formData.dd_type_codes.length} of {ddTypes.length} types selected</span>
                    ) : (
                      <span>No types selected</span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setFormData(prev => ({ ...prev, dd_type_codes: filteredDdTypes.map(dd => dd.code) }))}
                      className="text-xs text-link"
                    >
                      Select All {ddTypeSearch || selectedCategory !== 'all' ? 'Filtered' : ''}
                    </button>
                    <span className="text-border">|</span>
                    <button
                      onClick={() => setFormData(prev => ({ ...prev, dd_type_codes: [] }))}
                      className="text-xs text-content-secondary hover:text-content"
                    >
                      Clear All
                    </button>
                  </div>
                </div>

                {/* DD Types Grid */}
                {filteredDdTypes.length === 0 ? (
                  <EmptyState
                    icon={FunnelIcon}
                    title="No due diligence types found matching your criteria."
                    action={(
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setDdTypeSearch('');
                          setSelectedCategory('all');
                        }}
                      >
                        Clear filters
                      </Button>
                    )}
                  />
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredDdTypes.map(dd => {
                    const isSelected = formData.dd_type_codes.includes(dd.code);
                    const IconComponent = getDdTypeIcon(dd);

                    return (
                      <div key={dd.code} className="relative h-36">
                        <label className={`relative flex flex-col h-full p-4 rounded-lg cursor-pointer ${
                          isSelected
                            ? 'border border-accent-blue bg-accent-blue/5'
                            : 'gradient-grey-border-hover'
                        }`}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => {
                              const checked = e.target.checked;
                              setFormData(prev => ({
                                ...prev,
                                dd_type_codes: checked
                                  ? [...prev.dd_type_codes, dd.code]
                                  : prev.dd_type_codes.filter(code => code !== dd.code)
                              }));
                            }}
                            className="sr-only"
                          />

                          {/* Selection indicator */}
                          <div className={`absolute top-3 right-3 w-5 h-5 rounded-full border-2 transition-all duration-200 ${
                            isSelected
                              ? 'bg-accent-blue border-accent-blue'
                              : 'border-border'
                          }`}>
                            {isSelected && (
                              <CheckCircleIcon className="w-5 h-5 text-content-inverse" />
                            )}
                          </div>

                          {/* Icon */}
                          <div className="mb-3 p-2 rounded-lg inline-flex items-center justify-center bg-surface-bg">
                            <IconComponent className={`w-6 h-6 ${
                              isSelected
                                ? 'text-accent-blue'
                                : 'text-content-secondary'
                            }`} />
                          </div>

                          {/* Content */}
                          <div className="flex-1">
                            <h3 className="text-sm font-semibold mb-1 leading-tight text-content">
                              {dd.name}
                            </h3>
                            {dd.description && (
                              <p className="text-xs leading-relaxed line-clamp-2 overflow-hidden text-content-secondary" title={dd.description}>
                                {dd.description}
                              </p>
                            )}
                          </div>
                        </label>
                      </div>
                    );
                  })}
                  </div>
                )}

                {formData.dd_type_codes.length === 0 && (
                  <p className="alert alert-error mt-4 flex items-center gap-2">
                    <ExclamationTriangleIcon className="w-4 h-4 flex-shrink-0" />
                    Please select at least one due diligence type to continue.
                  </p>
                )}
              </div>


              {/* Selected Asset Manager / Fund Preview */}
              {selectedCompany && (
                <div className="alert alert-info mb-8">
                  <h3 className="text-sm font-medium mb-2">Selected Asset Manager / Fund</h3>
                  <div className="text-sm text-content">
                    <p><strong>{selectedCompany.name}</strong></p>
                    {selectedCompany.website_url && (
                      <p className="mt-1">
                        <a href={selectedCompany.website_url} target="_blank" rel="noopener noreferrer" className="text-link">
                          {selectedCompany.website_url}
                        </a>
                      </p>
                    )}
                    {selectedCompany.description && (
                      <p className="mt-1">{selectedCompany.description}</p>
                    )}
                  </div>

                  {/* The management company drives how the engine searches, so it
                      is editable here: a company created earlier has none, and no
                      other screen can set one. */}
                  <div className="mt-3 pt-3 border-t border-accent-blue/30">
                    {editingManager ? (
                      <div className="space-y-3">
                        <Input
                          label="Management company"
                          type="text"
                          value={editingManager.management_company_name}
                          onChange={(e) => setEditingManager(prev => ({
                            ...prev, management_company_name: e.target.value
                          }))}
                          placeholder="Company running the fund"
                        />
                        <Input
                          label="Management company website"
                          type="url"
                          value={editingManager.management_company_website}
                          onChange={(e) => setEditingManager(prev => ({
                            ...prev, management_company_website: e.target.value
                          }))}
                          placeholder="https://example.com"
                        />
                        <div className="flex space-x-2">
                          <Button
                            variant="primary"
                            onClick={() => handleSaveManager(selectedCompany)}
                            disabled={loading}
                          >
                            Save
                          </Button>
                          <Button variant="secondary" onClick={() => setEditingManager(null)}>
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-start justify-between">
                        <div className="text-sm text-content">
                          <p className="text-xs font-medium text-accent-blue">Management company</p>
                          {selectedCompany.management_company_name ? (
                            <>
                              <p>{selectedCompany.management_company_name}</p>
                              {selectedCompany.management_company_website && (
                                <a
                                  href={selectedCompany.management_company_website}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-link"
                                >
                                  {selectedCompany.management_company_website}
                                </a>
                              )}
                            </>
                          ) : (
                            <p className="text-content-secondary italic">
                              Not set — the engine will not be able to tell fund-level
                              questions from management-company ones.
                            </p>
                          )}
                        </div>
                        <button
                          type="button"
                          onClick={() => setEditingManager({
                            management_company_name: selectedCompany.management_company_name || '',
                            management_company_website: selectedCompany.management_company_website || ''
                          })}
                          className="text-sm text-link underline"
                        >
                          Edit
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-end space-x-3">
                <Button
                  variant="secondary"
                  onClick={() => navigate('/')}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  onClick={handleCreateSession}
                  disabled={!formData.company_id || !formData.name || formData.dd_type_codes.length === 0 || loading}
                  loading={loading}
                >
                  {loading ? 'Creating...' : 'Create Session'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </Layout>
    );
};

export default SessionCreate;
