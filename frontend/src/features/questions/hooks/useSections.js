import { useState } from 'react';
import { questionsAPI } from '../../../services/api';
import toast from 'react-hot-toast';

export const useSections = (selectedDdType, onRefresh) => {
  const [editingSection, setEditingSection] = useState(null);
  const [showSectionModal, setShowSectionModal] = useState(false);

  const createSection = () => {
    setEditingSection({
      title: '',
      order_index: selectedDdType?.sections?.length || 0,
      description: ''
    });
    setShowSectionModal(true);
  };

  const editSection = (section) => {
    setEditingSection({ ...section });
    setShowSectionModal(true);
  };

  const saveSection = async () => {
    if (!editingSection.title) {
      toast.error('Section title is required');
      return false;
    }

    try {
      if (editingSection.id) {
        await questionsAPI.updateSection(editingSection.id, editingSection);
        toast.success('Section updated successfully');
      } else {
        await questionsAPI.createSection(selectedDdType.code, editingSection);
        toast.success('Section created successfully');
      }

      setShowSectionModal(false);
      setEditingSection(null);
      await onRefresh();
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save section');
      return false;
    }
  };

  const deleteSection = async (sectionId) => {
    if (!window.confirm('Are you sure you want to delete this section? All questions in this section will also be deleted.')) {
      return false;
    }

    try {
      await questionsAPI.deleteSection(sectionId);
      toast.success('Section deleted successfully');
      await onRefresh();
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete section');
      return false;
    }
  };

  const reorderSection = async (sectionId, newOrder) => {
    try {
      await questionsAPI.reorderSection(sectionId, newOrder);
      await onRefresh();
      return true;
    } catch (error) {
      toast.error('Failed to reorder section');
      return false;
    }
  };

  const cancelEdit = () => {
    setShowSectionModal(false);
    setEditingSection(null);
  };

  return {
    editingSection,
    setEditingSection,
    showSectionModal,
    createSection,
    editSection,
    saveSection,
    deleteSection,
    reorderSection,
    cancelEdit
  };
};
