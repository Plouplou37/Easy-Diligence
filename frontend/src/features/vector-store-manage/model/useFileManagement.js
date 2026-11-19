import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { vectorStoresAPI } from '@/entities/vector-store';
import { useConfirm } from '@/shared/lib/confirm';

/** The files of the selected vector store, and their removal. */
export const useFileManagement = (selectedStore, onFileChange) => {
  const confirm = useConfirm();
  const [files, setFiles] = useState([]);
  const [filesLoading, setFilesLoading] = useState(false);
  const storeId = selectedStore?.id;

  const loadFiles = useCallback(async () => {
    if (!storeId) return;
    setFilesLoading(true);
    try {
      const response = await vectorStoresAPI.getFiles(storeId);
      setFiles(response.data.files || []);
    } catch {
      toast.error('Failed to load files');
      setFiles([]);
    } finally {
      setFilesLoading(false);
    }
  }, [storeId]);

  useEffect(() => {
    setFiles([]);
    loadFiles();
  }, [loadFiles]);

  const removeFile = async fileId => {
    const file = files.find(item => item.id === fileId);
    const confirmed = await confirm({
      title: 'Remove file',
      message:
        `Remove ${file?.filename ? `"${file.filename}"` : 'this file'} from the vector store? ` +
        'The DD runs that use this store will no longer search it.',
      confirmLabel: 'Remove',
      danger: true,
    });
    if (!confirmed) return;
    try {
      await vectorStoresAPI.removeFile(storeId, fileId);
      toast.success('File removed successfully');
      await loadFiles();
      await onFileChange();
    } catch {
      toast.error('Failed to remove file');
    }
  };

  return { files, filesLoading, loadFiles, removeFile };
};
