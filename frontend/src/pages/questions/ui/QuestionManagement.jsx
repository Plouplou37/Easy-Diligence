import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { PlusIcon, FolderIcon } from '@heroicons/react/24/outline';
import { Button, EmptyState, LoadingSpinner, PageHeader, pageLayout, panel, sectionHeader } from '@/shared/ui';
import DDTypeSelector from './DDTypeSelector';
import SectionCard from './SectionCard';
import QuestionEditor from './QuestionEditor';
import SectionEditor from './SectionEditor';
import { useDDTypes } from '../model/useDDTypes';
import { useSections } from '../model/useSections';
import { useQuestions } from '../model/useQuestions';
import { useDragDrop } from '../model/useDragDrop';

const QuestionManagement = () => {
  const [searchParams] = useSearchParams();

  const ddTypeHook = useDDTypes(searchParams.get('dd_type_code'));
  const sectionHook = useSections(ddTypeHook.selectedDdType, ddTypeHook.refreshSelectedDdType);
  const questionHook = useQuestions(ddTypeHook.selectedDdType, ddTypeHook.refreshSelectedDdType);

  const dragDropHook = useDragDrop(
    sectionHook.reorderSection,
    questionHook.reorderQuestion
  );

  const isValidated = ddTypeHook.selectedDdType?.is_validated || false;

  if (ddTypeHook.loading) {
    return (
      <>
        <div className="flex justify-center items-center h-64">
          <LoadingSpinner size="lg" text="Loading DD types..." />
        </div>
      </>
    );
  }

  return (
    <>
      <div className={pageLayout.container}>
        <PageHeader
          breadcrumb={[{ label: 'DD Types', href: '/dd-types' }, { label: 'Questions' }]}
          title="Question Management"
          subtitle="Manage questions and sections for DD types"
        />

        <DDTypeSelector
          ddTypes={ddTypeHook.ddTypes}
          selectedCode={ddTypeHook.selectedDdTypeCode}
          onChange={ddTypeHook.changeDdType}
          onValidate={ddTypeHook.validateDdType}
          onDelete={ddTypeHook.deleteDdType}
          selectedDdType={ddTypeHook.selectedDdType}
        />

        {ddTypeHook.selectedDdType && (
          <>
            <div className="flex items-center justify-between gap-4">
              <div className={`${sectionHeader.wrapper} flex-1`}>
                <h2 className={sectionHeader.title}>
                  Sections & Questions
                </h2>
                <div className={sectionHeader.hairline} />
              </div>
              {!isValidated && (
                <Button
                  onClick={sectionHook.createSection}
                  variant="primary"
                  icon={PlusIcon}
                >
                  Add Section
                </Button>
              )}
            </div>

            {ddTypeHook.selectedDdType.sections && ddTypeHook.selectedDdType.sections.length > 0 ? (
              <div className="space-y-4">
                {[...ddTypeHook.selectedDdType.sections]
                  .sort((a, b) => a.order_index - b.order_index)
                  .map((section) => (
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
                      onDrop: dragDropHook.handleSectionDrop
                    }}
                    questionDragHandlers={{
                      onDragStart: dragDropHook.handleQuestionDragStart,
                      onDragOver: dragDropHook.handleQuestionDragOver,
                      onDragLeave: dragDropHook.handleQuestionDragLeave,
                      onDrop: dragDropHook.handleQuestionDrop
                    }}
                    dragOverSection={dragDropHook.dragOverSection}
                    dragOverQuestion={dragDropHook.dragOverQuestion}
                  />
                ))}
              </div>
            ) : (
              <div className={panel.base}>
                <EmptyState
                  icon={FolderIcon}
                  title="No sections"
                  text="Get started by creating a section for this DD type."
                  action={!isValidated && (
                    <Button onClick={sectionHook.createSection} variant="primary" icon={PlusIcon}>
                      Create Section
                    </Button>
                  )}
                />
              </div>
            )}
          </>
        )}

        <QuestionEditor
          question={questionHook.editingQuestion}
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
    </>
  );
};

export default QuestionManagement;
