import { useState } from 'react';
import toast from 'react-hot-toast';
import { vectorStoresAPI } from '@/entities/vector-store';

const setStatus = (id, status) => (files) =>
  files.map((file) => (file.id === id ? { ...file, status } : file));

/**
 * Files chosen for a vector store, then sent one by one; each shows its own
 * outcome. `onUploadComplete` runs once all were tried.
 */
export const useFileUpload = (selectedStore, onUploadComplete) => {
  const [stagedFiles, setStagedFiles] = useState([]);
  const [uploadLoading, setUploadLoading] = useState(false);

  /** Stage the files of a file input or of a drop (a FileList). */
  const addFiles = (fileList) => {
    const added = Array.from(fileList).map((file, index) => ({
      id: `${file.name}-${Date.now()}-${index}`,
      file,
      name: file.name,
      size: file.size,
      status: 'pending',
    }));
    setStagedFiles((previous) => [...previous, ...added]);
  };

  const removeStagedFile = (fileId) => {
    setStagedFiles((previous) => previous.filter((file) => file.id !== fileId));
  };

  const confirmUpload = async () => {
    const pending = stagedFiles.filter((file) => file.status === 'pending');
    if (!pending.length) return;
    setUploadLoading(true);
    let succeeded = 0;
    let failed = 0;
    for (const staged of pending) {
      setStagedFiles(setStatus(staged.id, 'uploading'));
      try {
        await vectorStoresAPI.uploadFile(selectedStore.id, staged.file);
        setStagedFiles(setStatus(staged.id, 'success'));
        succeeded += 1;
      } catch {
        setStagedFiles(setStatus(staged.id, 'error'));
        failed += 1;
      }
    }
    if (succeeded > 0) toast.success(`${succeeded} file${succeeded > 1 ? 's' : ''} uploaded successfully`);
    if (failed > 0) toast.error(`${failed} file${failed > 1 ? 's' : ''} failed to upload`);
    setUploadLoading(false);
    // The failed ones stay listed, so the user sees which.
    setStagedFiles((previous) => previous.filter((file) => file.status === 'error'));
    await onUploadComplete({ failed });
  };

  return { stagedFiles, uploadLoading, addFiles, removeStagedFile, confirmUpload };
};
