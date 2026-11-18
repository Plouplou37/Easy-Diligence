import { useState, useEffect } from 'react';
import { vectorStoresAPI } from '../../../services/api';
import toast from 'react-hot-toast';

export const useFileManagement = (selectedStore, onFileChange) => {
  const [files, setFiles] = useState([]);
  const [filesLoading, setFilesLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [attributesForm, setAttributesForm] = useState({});

  useEffect(() => {
    if (selectedStore) {
      setFiles([]);
      loadFiles();
    } else {
      setFiles([]);
    }
  }, [selectedStore?.id]);

  const loadFiles = async () => {
    if (!selectedStore) return;

    try {
      setFilesLoading(true);
      const response = await vectorStoresAPI.getFiles(selectedStore.id);
      setFiles(response.data.files || []);
    } catch (error) {
      toast.error('Failed to load files');
      setFiles([]);
    } finally {
      setFilesLoading(false);
    }
  };

  const removeFile = async (fileId) => {
    if (!confirm('Are you sure you want to remove this file from the vector store?')) {
      return;
    }

    try {
      await vectorStoresAPI.removeFile(selectedStore.id, fileId);
      toast.success('File removed successfully');
      await loadFiles();
      await onFileChange();
    } catch (error) {
      toast.error('Failed to remove file');
    }
  };

  const editFileAttributes = (file) => {
    setSelectedFile(file);
    setAttributesForm(file.attributes || {});
  };

  const addAttribute = () => {
    setAttributesForm({
      ...attributesForm,
      '': ''
    });
  };

  const changeAttribute = (oldKey, newKey, value) => {
    const newForm = { ...attributesForm };
    if (oldKey !== newKey && oldKey !== '') {
      delete newForm[oldKey];
    }
    if (newKey !== '') {
      newForm[newKey] = value;
    }
    setAttributesForm(newForm);
  };

  const removeAttribute = (key) => {
    const newForm = { ...attributesForm };
    delete newForm[key];
    setAttributesForm(newForm);
  };

  const saveAttributes = async () => {
    try {
      await vectorStoresAPI.updateFileAttributes(selectedStore.id, selectedFile.id, attributesForm);
      toast.success('File attributes updated successfully');
      await loadFiles();
      return true;
    } catch (error) {
      toast.error('Failed to update file attributes');
      return false;
    }
  };

  return {
    files,
    filesLoading,
    selectedFile,
    setSelectedFile,
    attributesForm,
    loadFiles,
    removeFile,
    editFileAttributes,
    addAttribute,
    changeAttribute,
    removeAttribute,
    saveAttributes
  };
};
