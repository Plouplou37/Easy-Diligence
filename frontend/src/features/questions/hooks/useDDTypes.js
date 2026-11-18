import { useState, useEffect } from 'react';
import { questionsAPI, ddTypesAPI } from '../../../services/api';
import toast from 'react-hot-toast';

export const useDDTypes = (initialCode) => {
  const [ddTypes, setDdTypes] = useState([]);
  const [selectedDdType, setSelectedDdType] = useState(null);
  const [selectedDdTypeCode, setSelectedDdTypeCode] = useState(initialCode || null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDdTypes();
  }, []);

  const loadDdTypes = async () => {
    try {
      setLoading(true);
      const response = await questionsAPI.getDdTypes();
      setDdTypes(response.data);

      if (selectedDdTypeCode) {
        const targetDdType = response.data.find(t => t.code === selectedDdTypeCode);
        if (targetDdType) {
          setSelectedDdType(targetDdType);
        }
      }
    } catch (error) {
      toast.error('Failed to load DD types');
    } finally {
      setLoading(false);
    }
  };

  const refreshSelectedDdType = async () => {
    if (!selectedDdType) return;

    try {
      const response = await questionsAPI.getDdTypes();
      setDdTypes(response.data);
      const updatedDdType = response.data.find(t => t.code === selectedDdType.code);
      if (updatedDdType) {
        setSelectedDdType(updatedDdType);
      }
    } catch (error) {
      // Silent error
    }
  };

  const changeDdType = async (ddTypeCode) => {
    setSelectedDdTypeCode(ddTypeCode);

    if (ddTypeCode) {
      const ddType = ddTypes.find(t => t.code === ddTypeCode);
      setSelectedDdType(ddType || null);
    } else {
      setSelectedDdType(null);
    }
  };

  const validateDdType = async () => {
    if (!selectedDdType) {
      toast.error('No DD type selected');
      return false;
    }

    if (selectedDdType.is_validated) {
      toast.error('DD type is already validated');
      return false;
    }

    if (!window.confirm('Are you sure you want to validate this DD type? Once validated, it cannot be modified.')) {
      return false;
    }

    try {
      await ddTypesAPI.validate(selectedDdType.code);
      toast.success('DD type validated successfully');

      setSelectedDdType(prev => ({
        ...prev,
        is_validated: true
      }));

      await refreshSelectedDdType();
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to validate DD type');
      return false;
    }
  };

  const deleteDdType = async () => {
    if (!selectedDdType) {
      toast.error('No DD type selected');
      return false;
    }

    if (selectedDdType.is_validated) {
      toast.error('Cannot delete a validated DD type');
      return false;
    }

    if (!window.confirm(`Are you sure you want to delete "${selectedDdType.name}"? This will delete all sections and questions.`)) {
      return false;
    }

    try {
      await ddTypesAPI.delete(selectedDdType.code);
      toast.success('DD type deleted successfully');
      setSelectedDdType(null);
      setSelectedDdTypeCode(null);
      await loadDdTypes();
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete DD type');
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
    deleteDdType
  };
};
