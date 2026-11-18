import { useState, useEffect } from 'react';
import { vectorStoresAPI } from '@/entities/vector-store';
import toast from 'react-hot-toast';

export const useFileManagement = (selectedStore, onFileChange) => {
  const [files, setFiles] = useState([]);
  const [filesLoading, setFilesLoading] = useState(false);

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

  return {
    files,
    filesLoading,
    loadFiles,
    removeFile,
  };
};
