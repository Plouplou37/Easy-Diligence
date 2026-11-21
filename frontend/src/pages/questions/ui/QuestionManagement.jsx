import { useSearchParams } from 'react-router-dom';
import {
  CheckCircleIcon,
  DocumentTextIcon,
  FolderIcon,
  PlusIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import {
  QuestionEditor,
  SectionEditor,
  useDragDrop,
  useQuestions,
  useSections,
} from '@/features/questionnaire-edit';
import {
  AiBadge,
  Button,
  EmptyState,
  LoadingSpinner,
  PageHeader,
  pageLayout,
  panel,
} from '@/shared/ui';
import { SectionCard } from '@/widgets/questionnaire-tree';
import { useDDTypes } from '../model/useDDTypes';
import DDTypeSelector from './DDTypeSelector';

/** A questionnaire's sections and questions, edited in place until it is validated. */
const QuestionManagement = () => {
  const [searchParams] = useSearchParams();

  const ddTypeHook = useDDTypes(searchParams.get('dd_type_code'));
  const sectionHook = useSections(ddTypeHook.selectedDdType, ddTypeHook.refreshSelectedDdType);
  const questionHook = useQuestions(ddTypeHook.selectedDdType, ddTypeHook.refreshSelectedDdType);

  const dragDropHook = useDragDrop(sectionHook.reorderSection, questionHook.reorderQuestion);

  const selected = ddTypeHook.selectedDdType;
  const isValidated = selected?.is_validated || false;
  const sections = [...(selected?.sections || [])].sort((a, b) => a.order_index - b.order_index);
  const editedSection = sections.find(
    section => section.id === questionHook.editingQuestion?.section_id
  );

  if (ddTypeHook.loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner size="lg" text="Loading the questionnaires…" />
      </div>
    );
  }

  return (
    <div className={pageLayout.container}>
      <PageHeader
        breadcrumb={[
          { label: 'Questionnaires', href: '/dd-types' },
          { label: selected?.name || 'Questions' },
        ]}
        title={selected?.name || 'Questions'}
        subtitle="The questions the AI answers, one by one, in this order."
        meta={
          <span className="inline-flex flex-wrap items-center gap-2 text-sm text-content-secondary">
            <AiBadge />
            marks what the model reads with each question
          </span>
        }
        actions={
          selected &&
          !isValidated && (
            <>
              <Button
                onClick={ddTypeHook.validateDdType}
                variant="secondary"
                icon={CheckCircleIcon}
                title="Freeze its sections and questions, for good"
              >
                Validate
              </Button>
              <Button
                onClick={ddTypeHook.deleteDdType}
                variant="danger"
                size="lg"
                icon={TrashIcon}
                title="Delete this questionnaire"
                aria-label="Delete this questionnaire"
              />
            </>
          )
        }
      />

      <DDTypeSelector
        ddTypes={ddTypeHook.ddTypes}
        selectedCode={ddTypeHook.selectedDdTypeCode}
        onChange={ddTypeHook.changeDdType}
        selectedDdType={selected}
      />

      {selected ? (
        <section aria-label="Sections and questions" className={`${panel.base} overflow-hidden`}>
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
            <div className="min-w-0">
              <h2 className="text-base font-semibold text-content">Sections and questions</h2>
              <p className="mt-0.5 text-sm text-content-muted">
                {isValidated
                  ? 'Open a section to read its questions.'
                  : 'Open a section to see its questions. Drag the handles to reorder.'}
              </p>
            </div>
            {!isValidated && (
              <Button onClick={sectionHook.createSection} variant="primary" icon={PlusIcon}>
                Add section
              </Button>
            )}
          </div>

          {sections.length > 0 ? (
            <ol className="divide-y divide-border">
              {sections.map(section => (
                <SectionCard
                  key={section.id}
                  section={section}
                  isValidated={isValidated}
                  onEditSection={sectionHook.editSection}
                  onDeleteSection={sectionHook.deleteSection}
                  onCreateQuestion={questionHook.createQuestion}
                  onEditQuestion={questionHook.editQuestion}
                  onDeleteQuestion={questionHook.deleteQuestion}
                  dragHandlers={{
                    onDragStart: dragDropHook.handleSectionDragStart,
                    onDragOver: dragDropHook.handleSectionDragOver,
                    onDragLeave: dragDropHook.handleSectionDragLeave,
                    onDrop: dragDropHook.handleSectionDrop,
                  }}
                  questionDragHandlers={{
                    onDragStart: dragDropHook.handleQuestionDragStart,
                    onDragOver: dragDropHook.handleQuestionDragOver,
                    onDragLeave: dragDropHook.handleQuestionDragLeave,
                    onDrop: dragDropHook.handleQuestionDrop,
                  }}
                  dragOverSection={dragDropHook.dragOverSection}
                  dragOverQuestion={dragDropHook.dragOverQuestion}
                />
              ))}
            </ol>
          ) : (
            <EmptyState
              icon={FolderIcon}
              title="No sections yet"
              text="A section groups the questions of one theme: its title and context are sent to the model with each of them."
              action={
                !isValidated && (
                  <Button onClick={sectionHook.createSection} variant="primary" icon={PlusIcon}>
                    Add the first section
                  </Button>
                )
              }
            />
          )}
        </section>
      ) : (
        <div className={panel.base}>
          <EmptyState
            icon={DocumentTextIcon}
            title="Choose a questionnaire"
            text={
              ddTypeHook.ddTypes.length > 0
                ? 'Its sections and questions show here.'
                : 'There is no active questionnaire yet: create one from the Questionnaires page.'
            }
          />
        </div>
      )}

      <QuestionEditor
        question={questionHook.editingQuestion}
        sectionTitle={editedSection?.title}
        onChange={questionHook.setEditingQuestion}
        onSave={questionHook.saveQuestion}
        onCancel={questionHook.cancelEdit}
      />

      <SectionEditor
        show={sectionHook.showSectionModal}
        section={sectionHook.editingSection}
        onChange={sectionHook.setEditingSection}
        onSave={sectionHook.saveSection}
        onCancel={sectionHook.cancelEdit}
      />
    </div>
  );
};

export default QuestionManagement;
