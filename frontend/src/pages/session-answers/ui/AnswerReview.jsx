import { useMemo, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { getSessionDdTypes } from '@/entities/session';
import { ExportMenu } from '@/features/session-actions';
import { SynthesisTab } from '@/features/summaries';
import { LoadingSpinner, PageHeader, pageLayout, tabs } from '@/shared/ui';
import { AnswersBoard, useAnswerFilters } from '@/widgets/answers-board';
import { useAnswers } from '../model/useAnswers';

const TABS = [
  { id: 'answers', label: 'Answers' },
  { id: 'synthesis', label: 'Synthesis' },
];

/** The answers of one DD type of a session, and its synthesis. */
const AnswerReview = () => {
  const { sessionId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const ddTypeCode = searchParams.get('dd_type') || '';
  // ?tab=synthesis opens the synthesis directly (link from the session page).
  const [activeTab, setActiveTab] = useState(
    searchParams.get('tab') === 'synthesis' ? 'synthesis' : 'answers'
  );

  const { session, answers, ddTypes, loading, reload, updateAnswer } = useAnswers(
    sessionId,
    ddTypeCode
  );
  const filters = useAnswerFilters(answers);

  // The DD types of this session, for the switcher.
  const sessionDdTypes = useMemo(() => {
    const listed = getSessionDdTypes(session, ddTypes, {});
    return listed.length > 0 ? listed : ddTypes.filter(ddType => ddType.code === ddTypeCode);
  }, [session, ddTypes, ddTypeCode]);
  const ddTypeName = ddTypes.find(ddType => ddType.code === ddTypeCode)?.name || ddTypeCode;

  const changeDdType = code => {
    filters.setSection('');
    const next = new URLSearchParams(searchParams);
    next.set('dd_type', code);
    setSearchParams(next, { replace: true });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" text="Loading session data..." />
      </div>
    );
  }

  return (
    <div className={pageLayout.container}>
      <PageHeader
        breadcrumb={[
          { label: session?.name || 'Session', href: `/session/${sessionId}` },
          { label: 'Answers' },
        ]}
        title={`Review Answers${ddTypeName ? `: ${ddTypeName}` : ''}`}
        subtitle={`Review and edit AI-generated answers for ${session?.name || 'this session'}`}
        actions={<ExportMenu sessionId={sessionId} answers={filters.filtered} />}
      />

      {/* Answers vs synthesis: both are per DD type. */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <nav className={tabs.group}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`${tabs.tab} ${activeTab === tab.id ? tabs.active : tabs.inactive}`}
              aria-current={activeTab === tab.id ? 'page' : undefined}
            >
              {tab.label}
              {activeTab === tab.id && <span className={tabs.indicator} />}
            </button>
          ))}
        </nav>
        {sessionDdTypes.length > 1 && (
          <label className="flex items-center gap-2 text-xs text-content-secondary">
            DD type
            <select
              value={ddTypeCode}
              onChange={event => changeDdType(event.target.value)}
              className="form-input py-1.5 text-sm"
            >
              {sessionDdTypes.map(ddType => (
                <option key={ddType.code} value={ddType.code}>
                  {ddType.name}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {activeTab === 'answers' ? (
        <AnswersBoard filters={filters} updateAnswer={updateAnswer} reload={reload} />
      ) : (
        <SynthesisTab sessionId={sessionId} ddTypeCode={ddTypeCode} ddTypeName={ddTypeName} />
      )}
    </div>
  );
};

export default AnswerReview;
