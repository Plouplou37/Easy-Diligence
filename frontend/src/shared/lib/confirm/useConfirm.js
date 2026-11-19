import { useContext } from 'react';
import { ConfirmContext } from './context';

/** The confirm function of the nearest ConfirmProvider. */
export const useConfirm = () => {
  const confirm = useContext(ConfirmContext);
  if (!confirm) throw new Error('useConfirm must be used within a ConfirmProvider');
  return confirm;
};
