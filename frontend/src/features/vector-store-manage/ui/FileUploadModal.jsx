import { Modal } from '@/shared/ui';
import FileUploader from './FileUploader';

/** The upload window of a document collection. `upload`: useFileUpload. */
const FileUploadModal = ({ isOpen, onClose, upload }) => (
  <Modal isOpen={isOpen} onClose={upload.uploadLoading ? undefined : onClose} title="Add documents">
    <FileUploader upload={upload} onClose={onClose} />
  </Modal>
);

export default FileUploadModal;
