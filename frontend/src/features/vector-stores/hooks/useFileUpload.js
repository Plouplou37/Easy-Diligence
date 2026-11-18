import { useState } from 'react';
import { vectorStoresAPI } from '../../../services/api';
import toast from 'react-hot-toast';

export const useFileUpload = (selectedStore, onUploadComplete) => {
  const [stagedFiles, setStagedFiles] = useState([]);
  const [uploadLoading, setUploadLoading] = useState(false);

  const handleFileSelection = (e) => {
    const selectedFiles = Array.from(e.target.files);

    const newStagedFiles = selectedFiles.map((file) => ({
      id: `${file.name}-${Date.now()}`,
      file,
      name: file.name,
      size: file.size,
      status: 'pending'
    }));

    setStagedFiles(prev => [...prev, ...newStagedFiles]);
  };

  const removeStagedFile = (fileId) => {
    setStagedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const confirmUpload = async () => {
    if (!stagedFiles.length) return;

    try {
      setUploadLoading(true);
      let successCount = 0;
      let failCount = 0;

      for (let i = 0; i < stagedFiles.length; i++) {
        const stagedFile = stagedFiles[i];

        try {
          setStagedFiles(prev => prev.map(f =>
            f.id === stagedFile.id ? { ...f, status: 'uploading' } : f
          ));

          await vectorStoresAPI.uploadFile(selectedStore.id, stagedFile.file);

          setStagedFiles(prev => prev.map(f =>
            f.id === stagedFile.id ? { ...f, status: 'success' } : f
          ));

          successCount++;
        } catch (error) {
          setStagedFiles(prev => prev.map(f =>
            f.id === stagedFile.id ? { ...f, status: 'error' } : f
          ));

          failCount++;
        }
      }

      if (successCount > 0) {
        toast.success(`${successCount} file${successCount > 1 ? 's' : ''} uploaded successfully`);
      }
      if (failCount > 0) {
        toast.error(`${failCount} file${failCount > 1 ? 's' : ''} failed to upload`);
      }

      await onUploadComplete();

      setTimeout(() => {
        setStagedFiles([]);
      }, 2000);
    } catch (error) {
      toast.error('Failed to upload files');
    } finally {
      setUploadLoading(false);
    }
  };

  return {
    stagedFiles,
    uploadLoading,
    handleFileSelection,
    removeStagedFile,
    confirmUpload
  };
};
