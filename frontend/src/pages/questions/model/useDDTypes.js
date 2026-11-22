import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { ddTypesAPI, fetchDdTypes } from '@/entities/dd-type';
import { errorMessage } from '@/shared/api';
import { useConfirm } from '@/shared/lib/confirm';

/**
 * The DD types with their questionnaires, the one being edited (`initialCode`
 * first: the ?dd_type= of the URL), and its validation and deletion.
 */
export const useDDTypes = initialCode => {
  const confirm = useConfirm();
  const [ddTypes, setDdTypes] = useState([]);
  const [selectedDdTypeCode, setSelectedDdTypeCode] = useState(initialCode || null);
  const [loading, setLoading] = useState(true);
  // Derived, so that a reload shows the selected type's new questions.
  const selectedDdType = ddTypes.find(ddType => ddType.code === selectedDdTypeCode) || null;

  // Inactive questionnaires too: their "Questions" button opened this page
  // empty, their questions out of reach.
  const loadDdTypes = useCallback(async () => {
    setLoading(true);
    try {
      setDdTypes(await fetchDdTypes({ withQuestions: true, activeOnly: false }));
    } catch {
      toast.error('The questionnaires could not be loaded');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDdTypes();
  }, [loadDdTypes]);

  // After a change to the questionnaire (which clears the cached list), behind
  // the page: no spinner, the open sections stay open.
  const refreshSelectedDdType = useCallback(async () => {
    try {
      setDdTypes(await fetchDdTypes({ withQuestions: true, activeOnly: false }));
    } catch {
      toast.error('Failed to reload the questionnaire');
    }
  }, []);

  const changeDdType = code => setSelectedDdTypeCode(code || null);

  const validateDdType = async () => {
    if (!selectedDdType || selectedDdType.is_validated) return false;
    const confirmed = await confirm({
      title: 'Validate questionnaire',
      message:
        `Validate "${selectedDdType.name}"? Its sections and questions are then frozen: ` +
        'they can no longer be changed. This cannot be undone.',
      confirmLabel: 'Validate',
      danger: true,
    });
    if (!confirmed) return false;
    try {
      await ddTypesAPI.validate(selectedDdType.code);
      toast.success('Questionnaire validated');
      await refreshSelectedDdType();
      return true;
    } catch (error) {
      toast.error(errorMessage(error, 'The questionnaire could not be validated'));
      return false;
    }
  };

  const deleteDdType = async () => {
    if (!selectedDdType || selectedDdType.is_validated) return false;
    const confirmed = await confirm({
      title: 'Delete questionnaire',
      message: `Delete "${selectedDdType.name}" with all its sections and questions? This cannot be undone.`,
      confirmLabel: 'Delete',
      danger: true,
    });
    if (!confirmed) return false;
    try {
      await ddTypesAPI.delete(selectedDdType.code);
      toast.success('Questionnaire deleted');
      setSelectedDdTypeCode(null);
      await refreshSelectedDdType();
      return true;
    } catch (error) {
      toast.error(errorMessage(error, 'The questionnaire could not be deleted'));
      return false;
    }
  };

  return {
    ddTypes,
    selectedDdType,
    selectedDdTypeCode,
    loading,
    loadDdTypes,
    refreshSelectedDdType,
    changeDdType,
    validateDdType,
    deleteDdType,
  };
};
