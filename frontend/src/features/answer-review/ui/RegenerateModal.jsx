import { Modal } from '@/shared/ui';
import RegenerateForm from './RegenerateForm';

/** The regeneration's guidance, in a dialog. Closing it drops what was typed. */
const RegenerateModal = ({ isOpen, onClose, onSubmit, loading }) => {
  const handleClose = () => {
    if (!loading) onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Regenerate the answer" size="md">
      <RegenerateForm onSubmit={onSubmit} onCancel={handleClose} loading={loading} />
    </Modal>
  );
};

export default RegenerateModal;
