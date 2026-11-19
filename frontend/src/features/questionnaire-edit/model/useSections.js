import { useState } from 'react';
import toast from 'react-hot-toast';
import { questionsAPI } from '@/entities/dd-type';
import { errorMessage } from '@/shared/api';
import { useConfirm } from '@/shared/lib/confirm';

export const useSections = (selectedDdType, onRefresh) => {
  const confirm = useConfirm();
  const [editingSection, setEditingSection] = useState(null);
  const [showSectionModal, setShowSectionModal] = useState(false);

  const createSection = () => {
    setEditingSection({
      title: '',
      order_index: selectedDdType?.sections?.length || 0,
      description: '',
    });
    setShowSectionModal(true);
  };

  const editSection = section => {
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
      toast.error(errorMessage(error, 'Failed to save section'));
      return false;
    }
  };

  const deleteSection = async sectionId => {
    const section = selectedDdType?.sections?.find(item => item.id === sectionId);
    const confirmed = await confirm({
      title: 'Delete section',
      message: `Delete the section "${section?.title || ''}" and all its questions? This cannot be undone.`,
      confirmLabel: 'Delete',
      danger: true,
    });
    if (!confirmed) return false;

    try {
      await questionsAPI.deleteSection(sectionId);
      toast.success('Section deleted successfully');
      await onRefresh();
      return true;
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to delete section'));
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
    cancelEdit,
  };
};
