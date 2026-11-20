import { useMemo, useState } from 'react';
import {
  ArrowPathRoundedSquareIcon,
  CheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ClockIcon,
  EyeIcon,
  EyeSlashIcon,
  PencilIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getSourceContent, parseSourcesFromString } from '@/entities/answer';
import { displayQuestionCode } from '@/entities/dd-type';
import { Badge, Button } from '@/shared/ui';
import SourcesList from './SourcesList';
import SourcesManager from './SourcesManager';
import VersionHistory from './VersionHistory';

// The model answers with markdown tables often enough to matter (22 of the 72
// answers of one full run). `prose` styles them but does not make them
// scrollable, so a wide one was clipped by the card's overflow-hidden with no
// way to reach the right-hand columns.
const MARKDOWN_COMPONENTS = {
  // `node` (react-markdown's syntax tree) must not reach the DOM.
  table: ({ node, ...props }) => (
    <div className="overflow-x-auto">
      <table {...props} />
    </div>
  ),
};

/**
 * One answer to review: its question, the answer (read, or edited through
 * `editor`, from useAnswerEditor), its sources and its versions (`history`,
 * from useVersionHistory).
 */
const AnswerCard = ({
  answer,
  isExpanded,
  onToggle,
  editor,
  history,
  onRevert,
  onStatusToggle,
  onRegenerate,
  isRegenerating,
}) => {
  const [showSources, setShowSources] = useState(false);
  const sources = useMemo(() => parseSourcesFromString(answer.sources), [answer.sources]);
  const shownSources = sources.filter(source => getSourceContent(source) !== null).length;
  const isEditing = editor.editingAnswer === answer.id;
  const showHistory = history.showVersionHistory[answer.id];
  const approved = answer.status === 'approved';

  return (
    <div className="p-6">
      <div
        className="mb-4 cursor-pointer hover:bg-surface-hover p-2 rounded-md transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {/* The full code stays reachable on hover: it is the unique id. */}
            <h3
              className="text-sm font-medium text-content"
              title={answer.question_code || undefined}
            >
              {displayQuestionCode(answer.question_code) || 'Question'}
            </h3>
            <Badge variant={approved ? 'success' : 'warning'}>
              {approved ? 'Approved' : 'Needs Review'}
            </Badge>
            <label
              className="flex items-center space-x-2 cursor-pointer"
              onClick={event => event.stopPropagation()}
            >
              <input
                type="checkbox"
                checked={approved}
                onChange={onStatusToggle}
                className="w-4 h-4 rounded-sm"
                title={approved ? 'Mark as Needs Review' : 'Mark as Approved'}
              />
              <span className="text-xs text-content-secondary">Validate</span>
            </label>
          </div>
          {isExpanded ? (
            <ChevronUpIcon className="w-4 h-4 text-content-muted" />
          ) : (
            <ChevronDownIcon className="w-4 h-4 text-content-muted" />
          )}
        </div>
        {/* whitespace-pre-line: imported questions carry their instructions
            on their own lines (Level, Topic, Applies to...). HTML collapses those
            newlines, turning six readable lines into one wall of text. */}
        <p className="form-surface p-3 mt-2 text-sm text-content whitespace-pre-line">
          {answer.question_text}
        </p>
      </div>

      {/* Animating grid rows rather than a max-height: the cap was 5000px, and
          the longest answer of one full run (36 449 characters) was cut in half
          with nothing on screen to say so. 0fr -> 1fr expands to the natural
          height, so nothing is ever clipped and the transition stays. */}
      <div
        className={`grid transition-all duration-300 ease-in-out ${
          isExpanded ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
        }`}
      >
        <div
          className={`space-y-4 overflow-hidden transition-transform duration-300 ${
            isExpanded ? 'translate-y-0' : '-translate-y-2'
          }`}
        >
          <div className="mb-4">
            <h4 className="text-sm font-medium text-content mb-2">Answer</h4>

            {isEditing ? (
              <div className="space-y-3">
                {/* Monospace, like the synthesis editor: this is markdown
                    source, and pipe tables are unreadable in a proportional font. */}
                <textarea
                  value={editor.editText}
                  onChange={event => editor.setEditText(event.target.value)}
                  rows={12}
                  className="form-input w-full px-3 py-2 text-sm font-mono"
                  placeholder="Edit the answer..."
                  aria-label="Answer"
                />
                <input
                  type="text"
                  value={editor.revisionNotes}
                  onChange={event => editor.setRevisionNotes(event.target.value)}
                  placeholder="Edit reason (optional)"
                  className="form-input w-full px-3 py-2 text-sm"
                  aria-label="Edit reason"
                />
                <SourcesManager
                  editingSources={editor.editingSources}
                  newSource={editor.newSource}
                  setNewSource={editor.setNewSource}
                  onAddSource={editor.addSource}
                  onRemoveSource={editor.removeSource}
                />
                <div className="flex space-x-2">
                  <Button
                    onClick={() => editor.saveEdit(answer.id)}
                    variant="success"
                    icon={CheckIcon}
                  >
                    Save
                  </Button>
                  <Button onClick={editor.cancelEdit} variant="secondary" icon={XMarkIcon}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <>
                <div className="bg-surface-bg rounded-md p-4 prose prose-sm max-w-none text-sm text-content">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
                    {answer.text}
                  </ReactMarkdown>
                </div>

                <div className="flex items-center space-x-2 mt-3">
                  <Button
                    onClick={() => editor.startEdit(answer, sources)}
                    variant="secondary"
                    icon={PencilIcon}
                  >
                    Edit Answer
                  </Button>
                  <Button
                    onClick={() => history.toggleVersionHistory(answer.id)}
                    variant="secondary"
                    icon={ClockIcon}
                  >
                    {showHistory ? 'Hide Versions' : 'Version History'}
                  </Button>
                  <Button
                    onClick={onRegenerate}
                    variant="secondary"
                    icon={ArrowPathRoundedSquareIcon}
                    disabled={isRegenerating}
                  >
                    {isRegenerating ? 'Regenerating…' : 'Regenerate'}
                  </Button>
                </div>

                {showHistory && (
                  <div className="mt-4 form-surface p-4">
                    <h4 className="text-sm font-medium text-content mb-3 flex items-center">
                      <ClockIcon className="w-4 h-4 mr-2 text-content-muted" />
                      Version History
                      <Badge variant="info" className="ml-2">
                        Current: v{answer.version}
                      </Badge>
                    </h4>
                    <VersionHistory
                      answerId={answer.id}
                      versions={history.versionHistory[answer.id]}
                      onRevert={onRevert}
                    />
                  </div>
                )}
              </>
            )}
          </div>

          {/* No margin of its own: the space-y of the block spaces it (Tailwind 3
              cancelled this mb-4; Tailwind 4 no longer does). */}
          {!isEditing && shownSources > 0 && (
            <div>
              <Button
                onClick={() => setShowSources(shown => !shown)}
                variant="ghost"
                size="sm"
                icon={showSources ? EyeSlashIcon : EyeIcon}
                className="mb-2"
              >
                Sources ({shownSources})
              </Button>
              {showSources && <SourcesList sources={sources} />}
            </div>
          )}
        </div>
      </div>

      {/* Tokens and processing time are technical: kept in the tooltip. */}
      {answer.created_at && (
        <div className="flex items-center space-x-4 text-xs text-content-muted">
          <span
            title={
              [
                answer.tokens_used ? `Tokens: ${answer.tokens_used}` : null,
                answer.processing_time
                  ? `Processing time: ${Math.round(answer.processing_time)} ms`
                  : null,
              ]
                .filter(Boolean)
                .join(' · ') || undefined
            }
          >
            Created: {new Date(answer.created_at).toLocaleString()}
          </span>
        </div>
      )}
    </div>
  );
};

export default AnswerCard;
