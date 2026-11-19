import { useState } from 'react';
import { EnvelopeIcon } from '@heroicons/react/24/outline';
import { useAuth } from '@/entities/viewer';
import { Button, Input, Modal, modalStyles } from '@/shared/ui';

/** Ask for a reset link. The answer is the same whether the address exists or not. */
export const ForgotPasswordModal = ({ isOpen, onClose, initialEmail = '' }) => {
  const { resetPassword } = useAuth();
  const [email, setEmail] = useState(initialEmail);
  const [sending, setSending] = useState(false);

  const close = () => {
    setEmail('');
    onClose();
  };

  const send = async (event) => {
    event.preventDefault();
    setSending(true);
    const result = await resetPassword(email);
    setSending(false);
    if (result.success) close();
  };

  return (
    <Modal isOpen={isOpen} onClose={close} title="Reset Password" size="sm">
      <form onSubmit={send}>
        <p className="text-sm text-content-secondary mb-4">
          Enter your email address: a link to choose a new password will be sent to it.
        </p>
        <Input
          label="Email address"
          type="email"
          required
          autoComplete="email"
          leftIcon={EnvelopeIcon}
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@example.com"
        />
        <div className={`${modalStyles.footer} -mx-5 -mb-4 mt-4`}>
          <Button type="button" variant="secondary" onClick={close}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={sending}>
            Send Reset Link
          </Button>
        </div>
      </form>
    </Modal>
  );
};
