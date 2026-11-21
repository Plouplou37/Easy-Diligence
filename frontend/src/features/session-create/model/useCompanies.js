import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { companyAPI } from '@/entities/company';
import { errorMessage } from '@/shared/api';
import { toPayload } from '../lib/fund';

/** The funds the user can open a due diligence on, with their creation and editing. */
export const useCompanies = () => {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const response = await companyAPI.list();
      setCompanies(response.data);
    } catch (error) {
      toast.error(errorMessage(error, 'The funds could not be loaded'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  /** Add a fund. Resolves to it, or null (a toast says why). */
  const create = async fields => {
    try {
      const response = await companyAPI.create(toPayload(fields));
      setCompanies(previous => [...previous, response.data]);
      return response.data;
    } catch (error) {
      toast.error(errorMessage(error, 'The fund could not be added'));
      return null;
    }
  };

  /** Replace the details of `company`. Resolves to the saved company, or null. */
  const save = async (company, fields) => {
    setSaving(true);
    try {
      // PUT /company/{id} takes a whole company, not a patch: every field is sent.
      const response = await companyAPI.update(company.id, toPayload(fields));
      setCompanies(previous =>
        previous.map(item => (item.id === company.id ? response.data : item))
      );
      toast.success("The fund's details are saved");
      return response.data;
    } catch (error) {
      toast.error(
        error.response?.status === 403
          ? 'Only the person who added this fund, or an administrator, can change its details'
          : errorMessage(error, "The fund's details could not be saved")
      );
      return null;
    } finally {
      setSaving(false);
    }
  };

  return { companies, loading, saving, create, save };
};
