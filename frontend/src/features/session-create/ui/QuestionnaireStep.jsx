import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ClipboardDocumentListIcon, FunnelIcon } from '@heroicons/react/24/outline';
import { AiBadge, Button, EmptyState, LoadingSpinner, SearchInput } from '@/shared/ui';
import { categoriesOf, ddTypeCategory } from '../lib/ddTypeCategory';
import { plural } from '../lib/text';
import { ChoiceCard } from './ChoiceCard';
import { FieldError } from './fields';

// Below this many questionnaires, the search and the categories only get in the way.
const FILTER_FROM = 7;
// Sections listed per questionnaire before "…and N more".
const SECTIONS_SHOWN = 8;

const Counts = ({ counts }) =>
  counts ? (
    <span className="text-xs text-content-muted tabular-nums whitespace-nowrap">
      {plural(counts.questions, 'question')} · {plural(counts.sections, 'section')}
    </span>
  ) : null;

/** The sections of the chosen questionnaires: what the AI will be asked. */
const SectionsOverview = ({ chosen }) => {
  const known = chosen.filter(questionnaire => questionnaire.sections?.length);
  if (known.length === 0) return null;
  return (
    <div className="form-surface flex flex-col gap-3 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold text-content">
          {known.length === 1
            ? `Sections of ${known[0].name}`
            : 'Sections of the chosen questionnaires'}
        </h3>
        <AiBadge>Questions and “where to look” sent to the AI</AiBadge>
      </div>
      {known.map(questionnaire => (
        <div key={questionnaire.code} className="flex flex-col gap-1">
          {known.length > 1 && (
            <p className="text-sm font-medium text-content">{questionnaire.name}</p>
          )}
          <ul className="list-disc space-y-0.5 pl-5 text-sm text-content-secondary">
            {questionnaire.sections.slice(0, SECTIONS_SHOWN).map(section => (
              <li key={section.id}>
                {section.section_code}. {section.title} —{' '}
                <span className="tabular-nums">{plural(section.questions.length, 'question')}</span>
              </li>
            ))}
            {questionnaire.sections.length > SECTIONS_SHOWN && (
              <li>…and {plural(questionnaire.sections.length - SECTIONS_SHOWN, 'more section')}</li>
            )}
          </ul>
        </div>
      ))}
    </div>
  );
};

/**
 * Step 3: the questionnaires (DD types) of the due diligence, one or more.
 * `questionnaires`: mergeQuestionnaires. `selected`: their codes.
 */
export const QuestionnaireStep = ({
  questionnaires,
  loading,
  failed,
  onRetry,
  selected,
  onChange,
  error,
}) => {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');

  if (loading) return <LoadingSpinner text="Loading the questionnaires..." />;
  if (failed) {
    return (
      <div className="alert alert-error flex flex-wrap items-center justify-between gap-3">
        <span>The questionnaires could not be loaded.</span>
        <Button type="button" variant="secondary" onClick={onRetry}>
          Try again
        </Button>
      </div>
    );
  }
  if (questionnaires.length === 0) {
    return (
      <EmptyState
        icon={ClipboardDocumentListIcon}
        title="No questionnaire is available"
        text="Create one, or activate one, on the Questionnaires page."
        action={
          <Link to="/dd-types" className="text-sm text-link">
            Open the questionnaires
          </Link>
        }
      />
    );
  }

  const categories = categoriesOf(questionnaires);
  const term = search.trim().toLowerCase();
  const shown = questionnaires.filter(
    questionnaire =>
      (!term ||
        questionnaire.name.toLowerCase().includes(term) ||
        questionnaire.description?.toLowerCase().includes(term)) &&
      (category === 'all' || ddTypeCategory(questionnaire.name) === category)
  );
  const filtering = Boolean(term) || category !== 'all';
  const chosen = questionnaires.filter(questionnaire => selected.includes(questionnaire.code));

  const toggle = code =>
    onChange(
      selected.includes(code) ? selected.filter(item => item !== code) : [...selected, code]
    );

  return (
    <div className="flex flex-col gap-5">
      {questionnaires.length >= FILTER_FROM && (
        <div className="flex flex-col gap-3">
          <SearchInput
            placeholder="Search the questionnaires..."
            value={search}
            onChange={setSearch}
            aria-label="Search the questionnaires"
            // Enter would submit the step.
            onKeyDown={event => event.key === 'Enter' && event.preventDefault()}
          />
          {categories.length > 1 && (
            <div className="flex flex-wrap items-center gap-2">
              <FunnelIcon aria-hidden="true" className="h-4 w-4 text-content-muted" />
              <span className="eyebrow mr-1">Category</span>
              {[{ key: 'all', label: 'All', count: questionnaires.length }, ...categories].map(
                item => (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => setCategory(item.key)}
                    data-active={category === item.key}
                    aria-pressed={category === item.key}
                    className="pill-action min-h-10"
                  >
                    {item.label} ({item.count})
                  </button>
                )
              )}
            </div>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-content-secondary" aria-live="polite">
          {selected.length > 0
            ? `${selected.length} of ${plural(questionnaires.length, 'questionnaire')} chosen`
            : 'No questionnaire chosen'}
        </p>
        <div className="flex gap-1">
          <Button
            type="button"
            variant="ghost"
            onClick={() =>
              onChange([
                ...new Set([...selected, ...shown.map(questionnaire => questionnaire.code)]),
              ])
            }
          >
            {filtering ? 'Choose the ones shown' : 'Choose all'}
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() => onChange([])}
            disabled={!selected.length}
          >
            Clear
          </Button>
        </div>
      </div>

      {shown.length === 0 ? (
        <EmptyState
          icon={FunnelIcon}
          title="No questionnaire matches the search."
          action={
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setSearch('');
                setCategory('all');
              }}
            >
              Clear the filters
            </Button>
          }
        />
      ) : (
        <fieldset
          id="questionnaires"
          tabIndex={-1}
          aria-describedby={error ? 'questionnaires-error' : undefined}
          className="focus:outline-hidden"
        >
          <legend className="sr-only">Questionnaires</legend>
          <div className="flex flex-col gap-2.5">
            {shown.map(questionnaire => (
              <ChoiceCard
                key={questionnaire.code}
                id={`questionnaire-${questionnaire.code}`}
                type="checkbox"
                checked={selected.includes(questionnaire.code)}
                onChange={() => toggle(questionnaire.code)}
                title={questionnaire.name}
                hint={questionnaire.description}
                aside={<Counts counts={questionnaire.counts} />}
              />
            ))}
          </div>
        </fieldset>
      )}
      <FieldError id="questionnaires-error">{error}</FieldError>

      <SectionsOverview chosen={chosen} />
    </div>
  );
};
