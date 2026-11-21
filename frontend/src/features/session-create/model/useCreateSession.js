import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { sessionAPI } from '@/entities/session';
import { vectorStoresAPI } from '@/entities/vector-store';
import { errorMessage } from '@/shared/api';

/**
 * Create the due diligence, then open its page: the new fund first when there
 * is one, then the session, then the document collection, assigned to the
 * whole session (every questionnaire without its own searches it). Nothing is
 * sent to the model: the run starts on the session's page.
 */
export const useCreateSession = () => {
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);

  /**
   * `fund`: useFundDraft. `details`: { name, description }. `ddTypeIds`: the
   * questionnaires, in their order. `storeId`: the collection, or null.
   */
  const create = async ({ fund, details, ddTypeIds, storeId }) => {
    setCreating(true);
    const company = fund.mode === 'new' ? await fund.createNew() : fund.company;
    if (!company) {
      setCreating(false);
      return;
    }

    let session;
    try {
      const response = await sessionAPI.create({
        company_id: company.id,
        name: details.name.trim(),
        description: details.description.trim() || null,
        dd_type_ids: ddTypeIds,
      });
      session = response.data;
    } catch (error) {
      toast.error(errorMessage(error, 'The due diligence could not be created'));
      setCreating(false);
      return;
    }

    let documentsAssigned = false;
    if (storeId) {
      try {
        await vectorStoresAPI.assignToSession(storeId, session.id, { dd_type_id: null });
        documentsAssigned = true;
      } catch (error) {
        toast.error(
          errorMessage(
            error,
            'The documents could not be attached to the due diligence: assign them on its page'
          )
        );
      }
    }

    toast.success('Due diligence created');
    navigate(`/session/${session.session_code || session.id}`, {
      state: { newSession: true, documentsAssigned },
    });
  };

  return { create, creating };
};
