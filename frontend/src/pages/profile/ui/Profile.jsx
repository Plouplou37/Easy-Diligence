import React, { useState } from 'react';
import {
  UserCircleIcon,
  EnvelopeIcon,
  BriefcaseIcon,
  CheckIcon,
  LockClosedIcon,
  EyeIcon,
  EyeSlashIcon,
  AtSymbolIcon
} from '@heroicons/react/24/outline';
import { useAuth } from '@/entities/viewer';
import toast from 'react-hot-toast';
import { Button, PageHeader, field, modalStyles, pageLayout, panel, sectionHeader } from '@/shared/ui';

const Profile = () => {
  const { user, updateProfile, changePassword } = useAuth();
  const [editing, setEditing] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false
  });
  const [formData, setFormData] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
    role: user?.role || 'user',
    company: user?.company || '',
    phone: user?.phone || ''
  });

  const handleSave = async () => {
    const result = await updateProfile(formData);
    if (result.success) {
      setEditing(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({ ...prev, [name]: value }));
  };

  const handleChangePassword = async () => {
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      toast.error('New passwords do not match');
      return;
    }

    if (passwordData.newPassword.length < 8) {
      toast.error('New password must be at least 8 characters long');
      return;
    }

    // Additional password validation to match backend requirements
    if (!/[A-Z]/.test(passwordData.newPassword)) {
      toast.error('New password must contain at least one uppercase letter');
      return;
    }

    if (!/[a-z]/.test(passwordData.newPassword)) {
      toast.error('New password must contain at least one lowercase letter');
      return;
    }

    if (!/\d/.test(passwordData.newPassword)) {
      toast.error('New password must contain at least one number');
      return;
    }

    const result = await changePassword(passwordData.currentPassword, passwordData.newPassword);
    if (result.success) {
      setShowPasswordModal(false);
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      });
      // Success message is handled by changePassword function
    }
  };

  return (
    <>
      <div className={pageLayout.container}>
        <PageHeader
          breadcrumb={[{ label: 'Profile' }]}
          title="Profile"
          subtitle="Your account details and password"
        />

        <div className={panel.base}>
          <div className={panel.header}>
            <div className="flex items-center justify-between gap-4">
              <div className={`${sectionHeader.wrapper} flex-1 min-w-0`}>
                <h2 className={sectionHeader.title}>
                  Profile Information
                </h2>
                <div className={sectionHeader.hairline} />
              </div>
              {!editing ? (
                <Button
                  onClick={() => setEditing(true)}
                  variant="secondary"
                >
                  Edit Profile
                </Button>
              ) : (
                <div className="flex space-x-2">
                  <Button
                    onClick={handleSave}
                    variant="success"
                    icon={CheckIcon}
                  >
                    Save
                  </Button>
                  <Button
                    onClick={() => {
                      setEditing(false);
                      setFormData({
                        full_name: user?.full_name || '',
                        email: user?.email || '',
                        role: user?.role || 'user',
                        company: user?.company || '',
                        phone: user?.phone || ''
                      });
                    }}
                    variant="secondary"
                  >
                    Cancel
                  </Button>
                </div>
              )}
            </div>
          </div>

          <div className={panel.body}>
            <div className="flex items-center mb-6">
              <UserCircleIcon className="h-20 w-20 text-content-muted" />
              <div className="ml-4">
                <h3 className="text-lg font-medium text-content">
                  {user?.full_name}
                </h3>
                <p className="text-sm text-content-secondary flex items-center">
                  <AtSymbolIcon className="w-3 h-3 mr-1" />
                  {user?.username}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="eyebrow block mb-1">
                  Full Name
                </label>
                {editing ? (
                  <input
                    type="text"
                    name="full_name"
                    value={formData.full_name}
                    onChange={handleChange}
                    className="form-input w-full px-3 py-2 text-sm"
                  />
                ) : (
                  <p className="text-sm text-content">{user?.full_name}</p>
                )}
              </div>

              <div>
                <label className="eyebrow block mb-1">
                  Email Address
                </label>
                {editing ? (
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    className="form-input w-full px-3 py-2 text-sm"
                  />
                ) : (
                  <p className="text-sm text-content flex items-center">
                    <EnvelopeIcon className="w-4 h-4 mr-2 text-content-muted" />
                    {user?.email}
                  </p>
                )}
              </div>

<div>
                <label className="eyebrow block mb-1">
                  Company
                </label>
                {editing ? (
                  <input
                    type="text"
                    name="company"
                    value={formData.company}
                    onChange={handleChange}
                    placeholder="Your company name"
                    className="form-input w-full px-3 py-2 text-sm"
                  />
                ) : (
                  <p className="text-sm text-content flex items-center">
                    <BriefcaseIcon className="w-4 h-4 mr-2 text-content-muted" />
                    {user?.company || 'Not specified'}
                  </p>
                )}
              </div>

              <div>
                <label className="eyebrow block mb-1">
                  Phone Number
                </label>
                {editing ? (
                  <input
                    type="tel"
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                    placeholder="Your phone number"
                    className="form-input w-full px-3 py-2 text-sm"
                  />
                ) : (
                  <p className="text-sm text-content">
                    {user?.phone || 'Not specified'}
                  </p>
                )}
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-border">
              <h4 className="eyebrow-content mb-3">
                Account Information
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="eyebrow">Account Type:</span>
                  <span className="ml-2 text-content">
                    {user?.role === 'admin' ? 'Administrator' : 'Standard User'}
                  </span>
                </div>
                {/* Was today's date whatever the account's age. */}
                {user?.created_at && (
                  <div>
                    <span className="eyebrow">Member Since:</span>
                    <span className="ml-2 text-content">
                      {new Date(user.created_at).toLocaleDateString()}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Security Settings */}
        <div className={panel.base}>
          <div className={panel.header}>
            <div className={sectionHeader.wrapper}>
              <h2 className={sectionHeader.title}>
                Security Settings
              </h2>
              <div className={sectionHeader.hairline} />
            </div>
          </div>
          <div className={panel.body}>
            <div className="form-surface p-4">
              <Button
                onClick={() => setShowPasswordModal(true)}
                variant="secondary"
              >
                Change Password
              </Button>
            </div>
          </div>
        </div>

        {/* Change Password Modal */}
        {showPasswordModal && (
          <div className={modalStyles.overlay}>
            <div className={`${modalStyles.panel} max-w-md`}>
              <div className={modalStyles.header}>
                <h3 className={modalStyles.title}>
                  Change Password
                </h3>
              </div>

              <div className={modalStyles.body}>
                <p className="text-sm text-content-secondary mb-4">
                  Password must be at least 8 characters and include uppercase, lowercase, and number.
                </p>

                <div className="space-y-4">
                  {/* Current Password */}
                  <div>
                    <label className={field.label}>
                      Current Password
                    </label>
                    <div className="relative">
                      <input
                        type={showPasswords.current ? 'text' : 'password'}
                        name="currentPassword"
                        value={passwordData.currentPassword}
                        onChange={handlePasswordChange}
                        className="form-input w-full px-3 py-2 pr-10 text-sm"
                        placeholder="Enter current password"
                      />
                      <button
                        type="button"
                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-content-muted hover:text-content transition-colors"
                        onClick={() => setShowPasswords(prev => ({ ...prev, current: !prev.current }))}
                      >
                        {showPasswords.current ? (
                          <EyeSlashIcon className="h-5 w-5" />
                        ) : (
                          <EyeIcon className="h-5 w-5" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* New Password */}
                  <div>
                    <label className={field.label}>
                      New Password
                    </label>
                    <div className="relative">
                      <input
                        type={showPasswords.new ? 'text' : 'password'}
                        name="newPassword"
                        value={passwordData.newPassword}
                        onChange={handlePasswordChange}
                        className="form-input w-full px-3 py-2 pr-10 text-sm"
                        placeholder="Enter new password"
                      />
                      <button
                        type="button"
                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-content-muted hover:text-content transition-colors"
                        onClick={() => setShowPasswords(prev => ({ ...prev, new: !prev.new }))}
                      >
                        {showPasswords.new ? (
                          <EyeSlashIcon className="h-5 w-5" />
                        ) : (
                          <EyeIcon className="h-5 w-5" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Confirm New Password */}
                  <div>
                    <label className={field.label}>
                      Confirm New Password
                    </label>
                    <div className="relative">
                      <input
                        type={showPasswords.confirm ? 'text' : 'password'}
                        name="confirmPassword"
                        value={passwordData.confirmPassword}
                        onChange={handlePasswordChange}
                        className="form-input w-full px-3 py-2 pr-10 text-sm"
                        placeholder="Confirm new password"
                      />
                      <button
                        type="button"
                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-content-muted hover:text-content transition-colors"
                        onClick={() => setShowPasswords(prev => ({ ...prev, confirm: !prev.confirm }))}
                      >
                        {showPasswords.confirm ? (
                          <EyeSlashIcon className="h-5 w-5" />
                        ) : (
                          <EyeIcon className="h-5 w-5" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div className={modalStyles.footer}>
                <Button
                  onClick={() => {
                    setShowPasswordModal(false);
                    setPasswordData({
                      currentPassword: '',
                      newPassword: '',
                      confirmPassword: ''
                    });
                  }}
                  variant="secondary"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleChangePassword}
                  variant="primary"
                >
                  Change Password
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default Profile;