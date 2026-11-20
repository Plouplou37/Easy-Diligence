import { getDdTypeIcon } from '@/entities/dd-type';
import { Badge, MiniProgressBar, StatusBadge, panel } from '@/shared/ui';
import { AssignedDocuments } from './AssignedDocuments';
import { RunActions } from './RunActions';
import { RunStatus } from './RunStatus';
import { SectionTiles, StructureTiles } from './SectionTiles';

/**
 * A DD type run of a session: its progress, its figures, the documents it
 * searches, and what can be done with it. The actions come from the page
 * (features/dd-run-control, features/vector-store-assign).
 */
const DDCard = ({
  ddType,
  progress,
  onStart,
  onResume,
  onPause,
  onView,
  onSynthesis,
  disabled = false,
  vectorStores = [],
  assignedVectorStore = null,
  onAssignVectorStore = null,
  onRemoveVectorStore = null,
}) => {
  const code = ddType.code;
  const status = progress?.status || 'not_started';
  // Outline icon guessed from the name: the stored `icon` is an emoji.
  const DdTypeIcon = getDdTypeIcon(ddType);
  // A deactivated type stays on screen so its answers remain readable; it just
  // cannot be run again.
  const isInactive = ddType.is_active === false;

  const done = progress?.questions_completed || 0;
  const total = progress?.total_questions || 0;
  const sections = progress?.sections_progress || [];
  // Which section is being worked on: the tiles carry only counters.
  const activeSection = sections.find(section => section.status === 'in_progress');
  const completedSections = sections.filter(section => section.status === 'completed').length;

  return (
    <div
      className={`${panel.base} overflow-hidden hover:shadow-md transition-shadow duration-200 h-112`}
    >
      <div className={panel.rail} />
      {/* The card height is fixed (28rem): paddings, header height and the
          compact buttons are sized so a running DD -- stats, current question
          and actions -- still fits inside it. */}
      <div className="pl-6 pr-5 py-5 h-full flex flex-col">
        <div className="h-18 flex items-center justify-between mb-4">
          <div className="flex items-start space-x-3 flex-1 min-w-0">
            <div className="p-2 rounded-lg bg-surface-bg shrink-0">
              <DdTypeIcon className="w-5 h-5 text-content-secondary" />
            </div>
            <div className="min-w-0 flex-1">
              <h3
                className="text-fluid-md font-medium text-content line-clamp-1"
                title={ddType.name}
              >
                {ddType.name}
              </h3>
              <p
                className="text-sm text-content-muted line-clamp-2 leading-tight"
                title={ddType.description}
              >
                {ddType.description}
              </p>
            </div>
          </div>
          <div className="shrink-0 ml-3 flex items-center gap-2">
            {isInactive && (
              <span title="This DD type has been deactivated: it is no longer offered for new sessions. Existing answers stay available.">
                <Badge variant="warning">Inactive</Badge>
              </span>
            )}
            <StatusBadge status={status} />
          </div>
        </div>

        <div className="flex-1 space-y-3">
          <div className="min-h-[80px] space-y-3">
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="eyebrow leading-4">Overall Progress</span>
                <span className="text-xs text-content-muted tabular-nums">
                  {total > 0 ? `${done}/${total}` : 'Not configured'}
                </span>
              </div>
              {total > 0 ? (
                <MiniProgressBar current={done} total={total} status={status} />
              ) : (
                <div className="w-full bg-surface-hover rounded-full h-1.5">
                  <div
                    className="bg-content-muted/40 h-1.5 rounded-full"
                    style={{ width: '0%' }}
                  ></div>
                </div>
              )}
            </div>

            <div>
              <div className="flex justify-between items-center mb-1 gap-2">
                <span className="eyebrow leading-4 truncate" title={activeSection?.name}>
                  {activeSection ? `Sections — ${activeSection.name}` : 'Sections'}
                </span>
                <span className="text-xs text-content-muted shrink-0">
                  {sections.length > 0
                    ? `${completedSections}/${sections.length} completed`
                    : 'Ready to start'}
                </span>
              </div>
              {sections.length > 0 ? (
                <SectionTiles sections={sections} />
              ) : (
                <StructureTiles ddTypeCode={code} parentStatus={progress?.status} />
              )}
            </div>
          </div>

          <RunStatus progress={progress} isInactive={isInactive} />
        </div>

        <AssignedDocuments
          code={code}
          vectorStores={vectorStores}
          assigned={assignedVectorStore}
          locked={disabled || status === 'in_progress'}
          onAssign={onAssignVectorStore}
          onRemove={onRemoveVectorStore}
        />

        <div className="flex justify-end pt-3 border-t border-border">
          <RunActions
            code={code}
            status={status}
            isInactive={isInactive}
            disabled={disabled}
            onStart={onStart}
            onResume={onResume}
            onPause={onPause}
            onView={onView}
            onSynthesis={onSynthesis}
          />
        </div>
      </div>
    </div>
  );
};

export default DDCard;
