import { useId } from 'react';
import { ArrowPathIcon } from '@heroicons/react/24/outline';
import { getSourceContent } from '@/entities/answer';
import { RegenerateForm, SourcesManager, VersionHistory } from '@/features/answer-review';
import { Badge } from '@/shared/ui';

/** A panel of the side area: a title, something beside it, the content. */
const Panel = ({ title, aside, children }) => {
  const id = useId();
  return (
    <section aria-labelledby={id} className="rounded-xl border border-border bg-surface">
      <div className="flex min-h-14 flex-wrap items-center justify-between gap-2 border-b border-border px-5 py-3">
        <h2 id={id} className="text-sm font-semibold text-content">
          {title}
        </h2>
        {aside}
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
};

/** The sources of the draft: the user adds or removes their own, saved with the answer. */
export const SourcesPanel = ({ draft }) => {
  const shown = draft.sources.filter(source => getSourceContent(source) !== null).length;
  return (
    <Panel
      title="Sources"
      aside={<span className="text-xs text-content-muted tabular-nums">{shown}</span>}
    >
      {shown === 0 && <p className="mb-3 text-sm text-content-muted">No source cited.</p>}
      <SourcesManager
        editingSources={draft.sources}
        newSource={draft.newSource}
        setNewSource={draft.setNewSource}
        onAddSource={draft.addSource}
        onRemoveSource={draft.removeSource}
        title={null}
        className=""
      />
      <p className="mt-3 text-xs text-content-muted">
        The sources added or removed here are saved with the answer.
      </p>
    </Panel>
  );
};

/**
 * A regeneration, on the page rather than in a dialog: it takes 15 to 30
 * seconds, and the rest of the window stays usable meanwhile.
 */
export const RegeneratePanel = ({ regenerating, onRegenerate }) => (
  <Panel title="Regenerate">
    {regenerating && (
      <p
        role="status"
        className="mb-4 flex items-start gap-2 rounded-lg border border-theme-ai-border bg-theme-ai-bg px-3 py-2 text-sm text-theme-ai"
      >
        <ArrowPathIcon className="mt-0.5 h-4 w-4 shrink-0 motion-safe:animate-spin" />
        <span>
          Regenerating… The AI is writing a new answer, which takes 15 to 30 seconds. You can keep
          reading and editing meanwhile.
        </span>
      </p>
    )}
    <RegenerateForm onSubmit={onRegenerate} loading={regenerating} />
  </Panel>
);

/** The versions of the answer, newest first, each one can be brought back. */
export const VersionsPanel = ({ answer, versions, onRevert }) => (
  <Panel title="Versions" aside={<Badge variant="info">Current: v{answer.version || 1}</Badge>}>
    {versions === undefined ? (
      <p className="text-sm text-content-muted">Loading the versions…</p>
    ) : (
      <div className="max-h-[36rem] overflow-y-auto">
        <VersionHistory answerId={answer.id} versions={versions} onRevert={onRevert} />
      </div>
    )}
  </Panel>
);
