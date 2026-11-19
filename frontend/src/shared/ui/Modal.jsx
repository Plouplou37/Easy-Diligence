import { useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { modalStyles } from './styles';

const Modal = ({ isOpen, onClose, title, children, size = 'md' }) => {
  // Escape closes the modal, like a click on the backdrop.
  useEffect(() => {
    if (!isOpen || !onClose) return undefined;
    const handleKeyDown = event => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-4xl',
    xl: 'max-w-6xl',
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        {/* Backdrop */}
        <div className="fixed inset-0 modal-backdrop animate-fade-in" onClick={onClose}></div>

        {/* Modal */}
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
          className={`${modalStyles.panel} ${sizeClasses[size] || sizeClasses.md} max-h-[90vh] overflow-hidden`}
        >
          {/* Header */}
          <div className={modalStyles.header}>
            <h2 id="modal-title" className={modalStyles.title}>
              {title}
            </h2>
            <button
              type="button"
              onClick={onClose}
              className={modalStyles.close}
              aria-label="Close"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="px-5 py-4 overflow-y-auto max-h-[calc(90vh-120px)]">{children}</div>
        </div>
      </div>
    </div>
  );
};

export default Modal;
