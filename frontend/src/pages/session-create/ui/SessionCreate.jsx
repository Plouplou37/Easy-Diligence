import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDdTypes } from '@/entities/dd-type';
import {
  AiPreview,
  FundStep,
  QuestionnaireStep,
  ReviewStep,
  StepHeading,
  StepList,
  fundStepErrors,
  mergeQuestionnaires,
  questionCount,
  questionExample,
  useCompanies,
  useCreateSession,
  useFundDraft,
} from '@/features/session-create';
import { useConfirm } from '@/shared/lib/confirm';
import { AiBadge, Button, PageHeader, pageLayout } from '@/shared/ui';
import { STEPS } from '../model/steps';
import { useDocumentsChoice } from '../model/useDocumentsChoice';
import { DocumentsStep } from './DocumentsStep';

const LAST = STEPS.length;

/**
 * "New due diligence", in four steps: the fund, the documents, the
 * questionnaires, the review. On the right, what the AI will receive, as the
 * draft stands. The due diligence is created at the last step; the run starts
 * on its page.
 */
const SessionCreate = () => {
  const navigate = useNavigate();
  const confirm = useConfirm();

  const companies = useCompanies();
  const fund = useFundDraft(companies);
  const [details, setDetails] = useState({ name: '', description: '' });
  const documents = useDocumentsChoice();
  const list = useDdTypes();
  const structure = useDdTypes({ withQuestions: true });
  // null until the user changes it: every questionnaire, by default.
  const [chosenCodes, setChosenCodes] = useState(null);
  const creation = useCreateSession();

  const [step, setStep] = useState(1);
  const [reached, setReached] = useState(1);
  // The steps whose errors show: those the user tried to leave.
  const [attempted, setAttempted] = useState(() => new Set());
  const [focusTarget, setFocusTarget] = useState(null);
  const headingRef = useRef(null);
  const shownStep = useRef(step);

  const questionnaires = useMemo(
    () => mergeQuestionnaires(list.ddTypes, structure.ddTypes),
    [list.ddTypes, structure.ddTypes]
  );
  const codes = chosenCodes ?? questionnaires.map(questionnaire => questionnaire.code);
  const chosen = questionnaires.filter(questionnaire => codes.includes(questionnaire.code));
  const questions = chosen.length ? questionCount(chosen) : 0;
  const example =
    chosen.map(questionExample).find(Boolean) ||
    // Before any is chosen, the first questionnaire shows what a question looks like.
    questionExample(questionnaires[0]);
  const collection = documents.chosen
    ? { name: documents.chosen.name, files: documents.fileCount }
    : null;

  const errorsOf = number => {
    if (number === 1) return fundStepErrors(fund, details);
    if (number === 2) return documents.errors();
    if (number === 3 && chosen.length === 0) {
      return { questionnaires: 'Choose at least one questionnaire.' };
    }
    return {};
  };
  const errors = attempted.has(step) ? errorsOf(step) : {};

  // A new step starts from its title; a failed attempt, from the first field to fix.
  useEffect(() => {
    if (shownStep.current === step) return;
    shownStep.current = step;
    headingRef.current?.focus();
  }, [step]);
  useEffect(() => {
    if (!focusTarget) return;
    document.getElementById(focusTarget)?.focus();
    setFocusTarget(null);
  }, [focusTarget]);

  /** Show step `number` with its errors. False when it has some. */
  const check = number => {
    const found = errorsOf(number);
    const first = Object.keys(found)[0];
    if (!first) return true;
    setStep(number);
    setAttempted(previous => new Set(previous).add(number));
    setFocusTarget(first);
    return false;
  };

  /** Back freely; forward once the steps passed are complete. */
  const goTo = number => {
    for (let passed = step; passed < number; passed += 1) {
      if (!check(passed)) return;
    }
    setStep(number);
    setReached(previous => Math.max(previous, number));
  };

  const create = () => {
    for (let number = 1; number < LAST; number += 1) {
      if (!check(number)) return;
    }
    creation.create({
      fund,
      details,
      ddTypeIds: chosen.map(questionnaire => questionnaire.id),
      storeId: documents.chosen?.id || null,
    });
  };

  const submit = event => {
    event.preventDefault();
    if (creation.creating) return;
    if (step < LAST) goTo(step + 1);
    else create();
  };

  const cancel = async () => {
    const started =
      details.name.trim() ||
      details.description.trim() ||
      fund.newFields.name.trim() ||
      fund.company ||
      documents.created;
    if (started) {
      const leave = await confirm({
        title: 'Leave this due diligence?',
        message: documents.created
          ? 'What you entered here is lost. The document collection you created stays, on the Documents page.'
          : 'What you entered here is lost.',
        confirmLabel: 'Leave',
        cancelLabel: 'Stay',
      });
      if (!leave) return;
    }
    navigate('/');
  };

  const meta = STEPS[step - 1];

  return (
    <div className={pageLayout.container}>
      <PageHeader
        breadcrumb={[{ label: 'New' }]}
        title="New due diligence"
        subtitle="Four steps. No question goes to OpenAI before you start the run, on the due diligence's page."
        actions={
          <p className="flex flex-wrap items-center gap-2 text-[0.8125rem] text-content-secondary">
            <AiBadge />
            marks every field the AI reads
          </p>
        }
      />

      <div className="flex flex-wrap items-start gap-6">
        <nav
          aria-label="Steps"
          className="min-w-0 flex-[1_1_220px] xl:sticky xl:top-(--navbar-spacing)"
        >
          <StepList
            steps={STEPS}
            current={step}
            reached={reached}
            onPick={goTo}
            note="You can come back to any step. The due diligence is created at the last one."
          />
        </nav>

        <section aria-labelledby="step-title" className="min-w-0 flex-[999_1_560px]">
          <form
            noValidate
            onSubmit={submit}
            className="flex flex-col gap-6 rounded-xl border border-border bg-surface p-5 sm:p-7"
          >
            <StepHeading
              number={step}
              total={LAST}
              title={meta.title}
              description={meta.description}
              headingRef={headingRef}
            />

            {step === 1 && (
              <FundStep
                companies={companies}
                fund={fund}
                details={details}
                onDetailsChange={(key, value) =>
                  setDetails(previous => ({ ...previous, [key]: value }))
                }
                errors={errors}
              />
            )}
            {step === 2 && (
              <DocumentsStep documents={documents} fundName={fund.fields.name} errors={errors} />
            )}
            {step === 3 && (
              <QuestionnaireStep
                questionnaires={questionnaires}
                loading={list.loading}
                failed={Boolean(list.error)}
                onRetry={() => {
                  list.reload();
                  structure.reload();
                }}
                selected={codes}
                onChange={setChosenCodes}
                error={errors.questionnaires}
              />
            )}
            {step === 4 && (
              <ReviewStep
                fields={fund.fields}
                details={details}
                collection={collection}
                chosen={chosen}
                questions={questions}
                onEdit={goTo}
              />
            )}

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-5">
              {step > 1 ? (
                <Button type="button" variant="secondary" size="lg" onClick={() => goTo(step - 1)}>
                  Back
                </Button>
              ) : (
                <Button type="button" variant="ghost" size="lg" onClick={cancel}>
                  Cancel
                </Button>
              )}
              <Button type="submit" variant="primary" size="lg" loading={creation.creating}>
                {step < LAST ? 'Continue' : 'Create the due diligence'}
              </Button>
            </div>
          </form>
        </section>

        <aside
          aria-label="What the AI receives"
          className="min-w-0 flex-[1_1_320px] xl:sticky xl:top-(--navbar-spacing) xl:max-h-[calc(100vh-var(--navbar-spacing)-1.5rem)] xl:overflow-y-auto"
        >
          <AiPreview fields={fund.fields} collection={collection} example={example} />
        </aside>
      </div>
    </div>
  );
};

export default SessionCreate;
