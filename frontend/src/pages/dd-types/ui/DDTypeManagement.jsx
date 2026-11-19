import { useState } from 'react';
import { DocumentTextIcon, PlusIcon } from '@heroicons/react/24/outline';
import { DdTypeFormModal, DdTypesTable, useDdTypeAdmin } from '@/features/dd-type-admin';
import { Button, EmptyState, LoadingSpinner, PageHeader, pageLayout, panel, sectionHeader, tableStyles } from '@/shared/ui';

// The form's state: closed, a new DD type, or the one being edited.
const CLOSED = { open: false, ddType: null };

const DDTypeManagement = () => {
  const admin = useDdTypeAdmin();
  const [form, setForm] = useState(CLOSED);

  if (admin.loading && admin.ddTypes.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" text="Loading DD types..." />
      </div>
    );
  }

  const openNew = () => setForm({ open: true, ddType: null });
  const save = (values) => (form.ddType ? admin.update(form.ddType, values) : admin.create(values));

  return (
    <div className={pageLayout.container}>
      <PageHeader
        breadcrumb={[{ label: 'DD Types' }]}
        title="DD Type Management"
        subtitle="Manage due diligence types available in the system"
        actions={
          <Button onClick={openNew} variant="primary" icon={PlusIcon}>
            Add DD Type
          </Button>
        }
      />

      <div className={`${panel.base} overflow-hidden`}>
        <div className={panel.header}>
          <div className={sectionHeader.wrapper}>
            <h2 className={sectionHeader.title}>Available DD Types</h2>
            <div className={sectionHeader.hairline} />
          </div>
        </div>
        <div className={tableStyles.wrapper}>
          {admin.ddTypes.length > 0 ? (
            <DdTypesTable
              ddTypes={admin.ddTypes}
              onEdit={(ddType) => setForm({ open: true, ddType })}
              onToggleActive={admin.toggleActive}
              onDelete={admin.remove}
            />
          ) : (
            <EmptyState
              icon={DocumentTextIcon}
              title="No DD types found."
              action={
                <Button onClick={openNew} variant="ghost" size="sm">
                  Create the first one
                </Button>
              }
            />
          )}
        </div>
      </div>

      {form.open && <DdTypeFormModal ddType={form.ddType} onSave={save} onClose={() => setForm(CLOSED)} />}
    </div>
  );
};

export default DDTypeManagement;
