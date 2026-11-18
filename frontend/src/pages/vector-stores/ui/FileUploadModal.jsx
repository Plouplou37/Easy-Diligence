import React from 'react';
import { Modal } from '@/shared/ui';
import FileUploader from './FileUploader';

const FileUploadModal = ({
  show,
  onClose,
  stagedFiles,
  onFileSelect,
  onRemoveFile,
  onConfirmUpload,
  uploading
}) => {
  return (
    <Modal
      isOpen={show}
      onClose={onClose}
      title="Upload Files to Vector Store"
    >
      <div className="py-4">
        <FileUploader
          stagedFiles={stagedFiles}
          onFileSelect={onFileSelect}
          onRemoveFile={onRemoveFile}
          onConfirmUpload={onConfirmUpload}
          uploading={uploading}
        />
      </div>
    </Modal>
  );
};

export default FileUploadModal;
