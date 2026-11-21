import { useState } from 'react';
import { DocumentTextIcon, PlusIcon } from '@heroicons/react/24/outline';
import { DdTypeFormModal, DdTypesTable, useDdTypeAdmin } from '@/features/dd-type-admin';
import { Button, EmptyState, LoadingSpinner, PageHeader, pageLayout, panel } from '@/shared/ui';

// The form's state: closed, a new questionnaire, or the one being edited.
const CLOSED = { open: false, ddType: null };

/** The questionnaires (DD types): the list, and the window that creates or edits one. */
const DDTypeManagement = () => {
  const admin = useDdTypeAdmin();
  const [form, setForm] = useState(CLOSED);

  if (admin.loading && admin.ddTypes.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner size="lg" text="Loading the questionnaires…" />
      </div>
    );
  }

  const openNew = () => setForm({ open: true, ddType: null });
  const save = values => (form.ddType ? admin.update(form.ddType, values) : admin.create(values));
  const validated = admin.ddTypes.filter(ddType => ddType.is_validated).length;
  const total = admin.ddTypes.length;

  return (
    <div className={pageLayout.container}>
      <PageHeader
        title="Questionnaires"
        subtitle={
          <span className="block max-w-3xl">
            The questions the AI answers in a due diligence, one by one, grouped in sections.
            Validate a questionnaire once it is final: its sections and questions are then frozen.
          </span>
        }
        actions={
          <Button onClick={openNew} variant="primary" icon={PlusIcon}>
            New questionnaire
          </Button>
        }
      />

      <div className={`${panel.base} overflow-hidden`}>
        {total > 0 ? (
          <>
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-border px-5 py-4">
              <h2 className="text-base font-semibold text-content">All questionnaires</h2>
              <p className="text-sm tabular-nums text-content-muted">
                {total} questionnaire{total === 1 ? '' : 's'}, {validated} validated
              </p>
            </div>
            <DdTypesTable
              ddTypes={admin.ddTypes}
              counts={admin.counts}
              onEdit={ddType => setForm({ open: true, ddType })}
              onToggleActive={admin.toggleActive}
              onDelete={admin.remove}
            />
          </>
        ) : (
          <EmptyState
            icon={DocumentTextIcon}
            title="No questionnaires yet"
            text="Start one empty, or import it from an Excel, CSV or JSON file."
            action={
              <Button onClick={openNew} variant="primary" icon={PlusIcon}>
                New questionnaire
              </Button>
            }
          />
        )}
      </div>

      {form.open && (
        <DdTypeFormModal ddType={form.ddType} onSave={save} onClose={() => setForm(CLOSED)} />
      )}
    </div>
  );
};

export default DDTypeManagement;
