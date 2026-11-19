import { useState } from 'react';
import { ChangePasswordModal, ProfileDetails } from '@/features/auth';
import { Button, PageHeader, pageLayout, panel, sectionHeader } from '@/shared/ui';

const Profile = () => {
  const [changingPassword, setChangingPassword] = useState(false);

  return (
    <div className={pageLayout.container}>
      <PageHeader
        breadcrumb={[{ label: 'Profile' }]}
        title="Profile"
        subtitle="Your account details and password"
      />

      <ProfileDetails />

      <div className={panel.base}>
        <div className={panel.header}>
          <div className={sectionHeader.wrapper}>
            <h2 className={sectionHeader.title}>Security Settings</h2>
            <div className={sectionHeader.hairline} />
          </div>
        </div>
        <div className={panel.body}>
          <div className="form-surface p-4">
            <Button onClick={() => setChangingPassword(true)} variant="secondary">
              Change Password
            </Button>
          </div>
        </div>
      </div>

      <ChangePasswordModal isOpen={changingPassword} onClose={() => setChangingPassword(false)} />
    </div>
  );
};

export default Profile;
