import React from 'react';
import { FolderIcon, ChevronUpIcon, ChevronDownIcon } from '@heroicons/react/24/outline';
import AnswerCard from './AnswerCard';
import { panel } from '@/shared/ui';

const SectionGroup = ({
  sectionName,
  answers,
  isExpanded,
  onToggleSection,
  expandedQuestions,
  onToggleQuestion,
  editingAnswer,
  editText,
  setEditText,
  revisionNotes,
  setRevisionNotes,
  editingSources,
  newSource,
  setNewSource,
  onStartEdit,
  onSaveEdit,
  onCancelEdit,
  onAddSource,
  onRemoveSource,
  showSources,
  onToggleSources,
  parseSourcesFromString,
  renderSourceContent,
  showVersionHistory,
  versionHistory,
  onToggleVersionHistory,
  onRevert,
  onStatusToggle,
  onRegenerate,
  regeneratingId
}) => {
  return (
    <div className={`${panel.base} overflow-hidden`}>
      <div
        className="px-6 py-4 border-b border-border cursor-pointer hover:bg-surface-hover transition-colors"
        onClick={onToggleSection}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <FolderIcon className="h-5 w-5 text-content-muted" />
            <h2 className="text-lg font-medium text-content">
              {sectionName}
            </h2>
            <span className="text-sm text-content-muted">
              ({answers.length} {answers.length === 1 ? 'question' : 'questions'})
            </span>
          </div>
          {isExpanded ? (
            <ChevronUpIcon className="h-5 w-5 text-content-muted" />
          ) : (
            <ChevronDownIcon className="h-5 w-5 text-content-muted" />
          )}
        </div>
      </div>

      <div className={`divide-y divide-border overflow-hidden transition-all duration-300 ease-in-out ${isExpanded ? 'max-h-[10000px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className={`transition-transform duration-300 ${isExpanded ? 'translate-y-0' : '-translate-y-2'}`}>
          {answers.map((answer) => {
            const sources = parseSourcesFromString(answer.sources);
            const isQuestionExpanded = expandedQuestions[answer.id];
            const isEditing = editingAnswer === answer.id;

            return (
              <AnswerCard
                key={answer.id}
                answer={answer}
                isExpanded={isQuestionExpanded}
                onToggle={() => onToggleQuestion(answer.id)}
                isEditing={isEditing}
                editText={editText}
                setEditText={setEditText}
                revisionNotes={revisionNotes}
                setRevisionNotes={setRevisionNotes}
                editingSources={editingSources}
                newSource={newSource}
                setNewSource={setNewSource}
                onEdit={() => onStartEdit(answer, sources)}
                onSave={() => onSaveEdit(answer.id)}
                onCancel={onCancelEdit}
                onAddSource={onAddSource}
                onRemoveSource={onRemoveSource}
                showSources={showSources[answer.id]}
                onToggleSources={() => onToggleSources(answer.id)}
                sources={sources}
                renderSourceContent={renderSourceContent}
                showVersionHistory={showVersionHistory[answer.id]}
                versionHistory={versionHistory[answer.id]}
                onToggleVersionHistory={() => onToggleVersionHistory(answer.id)}
                onRevert={onRevert}
                onStatusToggle={() => onStatusToggle(answer.id, answer.status)}
                onRegenerate={onRegenerate ? () => onRegenerate(answer.id) : undefined}
                isRegenerating={regeneratingId === answer.id}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default SectionGroup;
