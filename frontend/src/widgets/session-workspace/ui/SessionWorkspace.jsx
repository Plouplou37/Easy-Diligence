import { useQuestionnaireStructures } from '../model/useQuestionnaireStructures';
import { Notices } from './Notices';
import { WorkspaceBody } from './WorkspaceBody';
import { WorkspaceHeader } from './WorkspaceHeader';

/**
 * A due diligence as one workspace: its header and actions, then its fund,
 * documents and questionnaires, the questions of the selected questionnaire
 * and the selected question.
 *
 * The page owns the data and the URL: `ddTypes` (the session's
 * questionnaires), `selected` (the one shown), `progressByCode` (the polled
 * progress of the runs), `overall` (getOverallStatus), `stale` (the poll
 * stopped answering), `runs` (useDdRunControl), `stores`
 * (useVectorStoreAssignments), `tab` ('questions' or 'synthesis'),
 * `justCreated` and `documentsAssigned` (from the creation page).
 */
export const SessionWorkspace = ({
  session,
  sessionId,
  ddTypes,
  selected,
  progressByCode,
  overall,
  stale,
  runs,
  stores,
  tab,
  onTabChange,
  onSelectDdType,
  justCreated,
  documentsAssigned,
  onDismissCreated,
}) => {
  const structures = useQuestionnaireStructures();
  const progress = selected ? progressByCode[selected.code] : undefined;
  const running = ddTypes.find(ddType => progressByCode[ddType.code]?.status === 'in_progress');
  // A run started at least once: there are answers to put in a report.
  const canExport = Object.keys(progressByCode).length > 0;

  return (
    <div className="mx-auto max-w-[100rem] space-y-5">
      <WorkspaceHeader
        session={session}
        sessionId={sessionId}
        ddType={selected}
        progress={progress}
        questionCount={selected ? structures.counts[selected.code] : 0}
        overall={overall}
        multiple={ddTypes.length > 1}
        stale={stale}
        runs={runs}
        canExport={canExport}
        tab={tab}
        onTabChange={onTabChange}
      />

      <Notices
        ddType={selected}
        progress={progress}
        runningName={running && running.code !== selected?.code ? running.name : null}
        justCreated={justCreated}
        documentsAssigned={documentsAssigned}
        onDismissCreated={onDismissCreated}
      />

      <WorkspaceBody
        key={selected?.code || 'none'}
        session={session}
        sessionId={sessionId}
        ddTypes={ddTypes}
        ddType={selected}
        progressByCode={progressByCode}
        runs={runs}
        stores={stores}
        structures={structures}
        tab={tab}
        onTabChange={onTabChange}
        onSelectDdType={onSelectDdType}
      />
    </div>
  );
};
