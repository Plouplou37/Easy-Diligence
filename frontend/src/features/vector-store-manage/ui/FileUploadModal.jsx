import { Modal } from '@/shared/ui';
import FileUploader from './FileUploader';

/** The upload window of a vector store. `upload`: useFileUpload. */
const FileUploadModal = ({ isOpen, onClose, upload }) => (
  <Modal isOpen={isOpen} onClose={upload.uploadLoading ? undefined : onClose} title="Upload Files to Vector Store">
    <div className="py-4">
      <FileUploader upload={upload} />
    </div>
  </Modal>
);

export default FileUploadModal;
