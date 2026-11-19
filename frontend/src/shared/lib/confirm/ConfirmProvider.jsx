import { useCallback, useRef, useState } from 'react';
import { Button } from '../../ui/Button';
import Modal from '../../ui/Modal';
import { modalStyles } from '../../ui/styles';
import { ConfirmContext } from './context';

/**
 * `confirm()` in the app's own dialog. `await confirm({ title, message })`
 * resolves to true when the user confirms, false otherwise (Cancel, Escape, the
 * close button or a click outside).
 */
export const ConfirmProvider = ({ children }) => {
  const [request, setRequest] = useState(null);
  const resolver = useRef(null);

  const confirm = useCallback(
    ({
      title = 'Please confirm',
      message,
      confirmLabel = 'Confirm',
      cancelLabel = 'Cancel',
      danger = false,
    }) =>
      new Promise(resolve => {
        resolver.current?.(false); // a request still open is dismissed
        resolver.current = resolve;
        setRequest({ title, message, confirmLabel, cancelLabel, danger });
      }),
    []
  );

  const answer = value => {
    resolver.current?.(value);
    resolver.current = null;
    setRequest(null);
  };

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      <Modal
        isOpen={Boolean(request)}
        onClose={() => answer(false)}
        title={request?.title}
        size="sm"
      >
        <p className="text-sm text-content-secondary whitespace-pre-line">{request?.message}</p>
        <div className={`${modalStyles.footer} -mx-5 -mb-4 mt-4`}>
          <Button variant="secondary" onClick={() => answer(false)}>
            {request?.cancelLabel}
          </Button>
          <Button variant={request?.danger ? 'danger' : 'primary'} onClick={() => answer(true)}>
            {request?.confirmLabel}
          </Button>
        </div>
      </Modal>
    </ConfirmContext.Provider>
  );
};
