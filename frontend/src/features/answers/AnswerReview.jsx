import React, { useState, useEffect, useMemo, useRef, useLayoutEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { DocumentArrowDownIcon, FolderIcon, ChevronDownIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import Layout from '../../components/Layout';
import AnswerFilters from './components/AnswerFilters';
import SectionGroup from './components/SectionGroup';
import RegenerateModal from './components/RegenerateModal';
import SynthesisTab from './components/SynthesisTab';
import { useAnswers } from './hooks/useAnswers';
import { useAnswerEditor } from './hooks/useAnswerEditor';
import { useVersionHistory } from './hooks/useVersionHistory';
import { parseSourcesFromString } from './hooks/useSourceParser';
import SourceContent from './components/SourceContent';
import { exportAnswersToCSV, downloadBlob } from './utils/exportHelpers';
import { answersAPI } from '../../services/api';
import { useDebounce } from '../../hooks';
import {
  Button,
  LoadingSpinner,
  PageHeader,
  StatTile,
  emptyState,
  menu,
  pageLayout,
  panel,
  tabs,
} from '../../components/ui';

const AnswerReview = () => {
  const { sessionId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDDType, setSelectedDDType] = useState(searchParams.get('dd_type') || '');
  const [selectedSection, setSelectedSection] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [showSources, setShowSources] = useState({});
  const [expandedSections, setExpandedSections] = useState({});
  const [expandedQuestions, setExpandedQuestions] = useState({});
  const [sectionsInitialized, setSectionsInitialized] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [regeneratingId, setRegeneratingId] = useState(null);
  const [regenerateTarget, setRegenerateTarget] = useState(null);
  // ?tab=synthesis opens the synthesis directly (link from the session page).
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') === 'synthesis' ? 'synthesis' : 'answers');

  // Scroll position persistence
  const scrollPositionRef = useRef(0);
  const shouldRestoreScrollRef = useRef(false);

  // Debounced search term for performance
  const debouncedSearchTerm = useDebounce(searchTerm, 300);

  const { session, answers, ddTypes, loading, loadData, updateAnswer } = useAnswers(
    sessionId,
    selectedDDType,
    selectedSection
  );

  // The DD types of this session, for the switcher. The page was reachable for
  // one type at a time only, through the session page.
  const sessionDdTypes = useMemo(() => {
    let codes = [];
    try {
      codes = JSON.parse(session?.dd_types_json || '[]').map((t) => t.code);
    } catch (error) {
      codes = [];
    }
    const listed = ddTypes.filter((t) => codes.includes(t.code));
    return listed.length > 0 ? listed : ddTypes.filter((t) => t.code === selectedDDType);
  }, [session, ddTypes, selectedDDType]);

  const changeDDType = (code) => {
    setSelectedDDType(code);
    setSelectedSection('');
    setSectionsInitialized(false);
    const next = new URLSearchParams(searchParams);
    next.set('dd_type', code);
    setSearchParams(next, { replace: true });
  };

  const versionHistoryHook = useVersionHistory();
  const editor = useAnswerEditor(updateAnswer, versionHistoryHook.fetchVersionHistory);

  // Initialize sections only once when answers first load
  useEffect(() => {
    if (answers.length > 0 && !sectionsInitialized) {
      const uniqueSections = [...new Set(answers.map(answer => answer.section_name).filter(Boolean))];
      const initialExpanded = {};
      uniqueSections.forEach(section => {
        // Only set if not already in state (preserve existing)
        if (!(section in expandedSections)) {
          initialExpanded[section] = false;
        } else {
          initialExpanded[section] = expandedSections[section];
        }
      });
      setExpandedSections(initialExpanded);
      setSectionsInitialized(true);
    }
  }, [answers.length, sectionsInitialized]);

  // Restore scroll position after state updates
  useLayoutEffect(() => {
    if (shouldRestoreScrollRef.current) {
      window.scrollTo(0, scrollPositionRef.current);
      shouldRestoreScrollRef.current = false;
    }
  });

  const toggleSources = (answerId) => {
    setShowSources(prev => ({
      ...prev,
      [answerId]: !prev[answerId]
    }));
  };

  const toggleSection = (sectionName) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionName]: !prev[sectionName]
    }));
  };

  const toggleQuestion = (answerId) => {
    setExpandedQuestions(prev => ({
      ...prev,
      [answerId]: !prev[answerId]
    }));
  };

  const handleStatusToggle = async (answerId, currentStatus) => {
    // Save scroll position before update
    scrollPositionRef.current = window.scrollY;
    shouldRestoreScrollRef.current = true;

    const newStatus = currentStatus === 'approved' ? 'needs_review' : 'approved';
    try {
      await updateAnswer(answerId, { status: newStatus });
    } catch (error) {
      console.error('Failed to update answer status:', error);
      shouldRestoreScrollRef.current = false;
    }
  };

  // Shared with the reading view (SourcesList), which rendered sources as inert
  // text until this logic left here.
  const renderSourceContent = (source) => <SourceContent source={source} />;

  // Opening the modal: the actual call happens on submit.
  const handleRegenerate = (answerId) => {
    setRegenerateTarget(answerId);
  };

  const submitRegenerate = async ({ instruction, referenceUrl, file }) => {
    const answerId = regenerateTarget;
    if (!answerId) return;
    scrollPositionRef.current = window.scrollY;
    shouldRestoreScrollRef.current = true;
    setRegeneratingId(answerId);
    try {
      await answersAPI.regenerate(answerId, { instruction, referenceUrl, file });
      await loadData();
      setRegenerateTarget(null);
      toast.success('Réponse régénérée.');
    } catch (error) {
      console.error('Failed to regenerate answer:', error);
      shouldRestoreScrollRef.current = false;
      toast.error('Échec de la régénération. Réessayez.');
    } finally {
      setRegeneratingId(null);
    }
  };

  const handleCsvExport = () => {
    setExportOpen(false);
    exportAnswersToCSV(filteredAnswers, sessionId);
  };

  const handlePdfExport = async () => {
    setExportOpen(false);
    setExporting(true);
    try {
      const res = await answersAPI.export(sessionId, 'pdf');
      downloadBlob(res.data, `session-${sessionId}-DD_Report.pdf`);
    } catch (error) {
      console.error('Failed to export answers:', error);
      toast.error('Export failed. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const filteredAnswers = (Array.isArray(answers) ? answers : []).filter(answer => {
    const matchesSearch = !debouncedSearchTerm ||
      (answer.question_text && answer.question_text.toLowerCase().includes(debouncedSearchTerm.toLowerCase())) ||
      (answer.text && answer.text.toLowerCase().includes(debouncedSearchTerm.toLowerCase()));

    const matchesSection = !selectedSection || answer.section_name === selectedSection;

    return matchesSearch && matchesSection;
  });

  const groupedAnswers = filteredAnswers.reduce((acc, answer) => {
    const sectionName = answer.section_name || 'Uncategorized';
    if (!acc[sectionName]) acc[sectionName] = [];
    acc[sectionName].push(answer);
    return acc;
  }, {});

  const answersBySection = groupedAnswers;
  const uniqueSections = [...new Set(answers.map(answer => answer.section_name).filter(Boolean))];

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen flex items-center justify-center">
          <LoadingSpinner size="lg" text="Loading session data..." />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className={pageLayout.container}>
        <PageHeader
          breadcrumb={[
            // Back to the session, not to the Dashboard ("Back to Sessions" went to /sessions).
            { label: session?.name || 'Session', href: `/session/${sessionId}` },
            { label: 'Answers' },
          ]}
          title={`Review Answers${selectedDDType ? `: ${ddTypes.find(t => t.code === selectedDDType)?.name || selectedDDType}` : ''}`}
          subtitle={`Review and edit AI-generated answers for ${session?.name || 'this session'}`}
          actions={(
            <div className="relative">
              <Button
                variant="primary"
                onClick={() => setExportOpen((open) => !open)}
                disabled={exporting}
              >
                <DocumentArrowDownIcon className="h-4 w-4" />
                {exporting ? 'Exporting…' : 'Export'}
                <ChevronDownIcon className="h-4 w-4" />
              </Button>
              {exportOpen && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setExportOpen(false)}
                  />
                  <div className={`absolute right-0 mt-2 w-48 z-20 py-1 ${menu.panel}`}>
                    <button
                      onClick={handlePdfExport}
                      className={menu.item}
                    >
                      PDF report
                    </button>
                    <button
                      onClick={handleCsvExport}
                      className={menu.item}
                    >
                      CSV (table)
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        />

        {/* Tabs: answers vs synthesis (synthesis is per DD type) */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <nav className={tabs.group}>
            {[
              { id: 'answers', label: 'Réponses' },
              { id: 'synthesis', label: 'Synthèse' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`${tabs.tab} ${activeTab === tab.id ? tabs.active : tabs.inactive}`}
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
                value={selectedDDType}
                onChange={(e) => changeDDType(e.target.value)}
                className="form-input py-1.5 text-sm"
              >
                {sessionDdTypes.map((t) => (
                  <option key={t.code} value={t.code}>{t.name}</option>
                ))}
              </select>
            </label>
          )}
        </div>

        {activeTab === 'answers' ? (
        <>
        {/* "To review" = every current answer not yet approved: a freshly
            generated answer is stored as `completed`, not `needs_review`. */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 mb-6">
          <StatTile label="Answers" value={filteredAnswers.length} />
          <StatTile
            label="To review"
            value={filteredAnswers.filter(a => a.status !== 'approved' && a.status !== 'failed').length}
          />
          <StatTile label="Approved" value={filteredAnswers.filter(a => a.status === 'approved').length} />
          <StatTile
            label="Edited"
            value={filteredAnswers.filter(a => a.version > 1).length}
            hint={`${Object.keys(answersBySection).length} sections`}
          />
        </div>

        <div className="mb-6">
          <AnswerFilters
            showFilters={showFilters}
            setShowFilters={setShowFilters}
            searchTerm={searchTerm}
            setSearchTerm={setSearchTerm}
            selectedSection={selectedSection}
            setSelectedSection={setSelectedSection}
            uniqueSections={uniqueSections}
          />
        </div>

        <div className="space-y-6 pb-12">
          {Object.keys(groupedAnswers).length === 0 ? (
            <div className={`${panel.base} ${emptyState.wrapper}`}>
              <FolderIcon className={emptyState.icon} />
              <h3 className={emptyState.title}>No answers found</h3>
              <p className={emptyState.text}>
                Try adjusting your filters or search terms.
              </p>
            </div>
          ) : (
            Object.entries(groupedAnswers).map(([sectionName, sectionAnswers]) => (
              <SectionGroup
                key={sectionName}
                sectionName={sectionName}
                answers={sectionAnswers}
                isExpanded={expandedSections[sectionName]}
                onToggleSection={() => toggleSection(sectionName)}
                expandedQuestions={expandedQuestions}
                onToggleQuestion={toggleQuestion}
                editingAnswer={editor.editingAnswer}
                editText={editor.editText}
                setEditText={editor.setEditText}
                revisionNotes={editor.revisionNotes}
                setRevisionNotes={editor.setRevisionNotes}
                editingSources={editor.editingSources}
                newSource={editor.newSource}
                setNewSource={editor.setNewSource}
                onStartEdit={editor.startEdit}
                onSaveEdit={editor.saveEdit}
                onCancelEdit={editor.cancelEdit}
                onAddSource={editor.addSource}
                onRemoveSource={editor.removeSource}
                showSources={showSources}
                onToggleSources={toggleSources}
                parseSourcesFromString={parseSourcesFromString}
                renderSourceContent={renderSourceContent}
                showVersionHistory={versionHistoryHook.showVersionHistory}
                versionHistory={versionHistoryHook.versionHistory}
                onToggleVersionHistory={versionHistoryHook.toggleVersionHistory}
                onRevert={(answerId, version) => versionHistoryHook.revertToVersion(answerId, version, loadData)}
                onStatusToggle={handleStatusToggle}
                onRegenerate={handleRegenerate}
                regeneratingId={regeneratingId}
              />
            ))
          )}
        </div>
        </>
        ) : (
          <SynthesisTab
            sessionId={sessionId}
            ddTypeCode={selectedDDType}
            ddTypeName={ddTypes.find(t => t.code === selectedDDType)?.name || selectedDDType}
          />
        )}
      </div>

      <RegenerateModal
        isOpen={regenerateTarget !== null}
        onClose={() => setRegenerateTarget(null)}
        onSubmit={submitRegenerate}
        loading={regeneratingId !== null}
      />
    </Layout>
  );
};

export default AnswerReview;
