import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { companyAPI } from '@/entities/company';
import { errorMessage } from '@/shared/api';

/** The funds the user can open a session on, with their creation and editing. */
export const useCompanies = () => {
  const [companies, setCompanies] = useState([]);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const response = await companyAPI.list();
      setCompanies(response.data);
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to load companies'));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  /** Resolves to the new company, or null. */
  const create = async values => {
    setSaving(true);
    try {
      const response = await companyAPI.create(values);
      setCompanies(previous => [...previous, response.data]);
      toast.success('Company created successfully');
      return response.data;
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to create company'));
      return null;
    } finally {
      setSaving(false);
    }
  };

  /** Set the management company of `company`. Resolves to true once saved. */
  const saveManager = async (company, manager) => {
    setSaving(true);
    try {
      // PUT /company/{id} takes a whole company, not a patch: it reassigns
      // every field it receives. Sending only the manager would blank the rest.
      const response = await companyAPI.update(company.id, {
        name: company.name,
        website_url: company.website_url,
        description: company.description,
        management_company_name: manager.management_company_name || null,
        management_company_website: manager.management_company_website || null,
      });
      setCompanies(previous =>
        previous.map(item => (item.id === company.id ? response.data : item))
      );
      toast.success('Management company saved');
      return true;
    } catch (error) {
      toast.error(
        error.response?.status === 403
          ? 'Only the owner of this company can edit it'
          : errorMessage(error, 'Failed to save management company')
      );
      return false;
    } finally {
      setSaving(false);
    }
  };

  return { companies, saving, create, saveManager };
};
