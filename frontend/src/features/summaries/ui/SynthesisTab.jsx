import {
  ArrowPathRoundedSquareIcon,
  ClockIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { Button, LoadingSpinner, emptyState, panel } from '@/shared/ui';
import { useSynthesis } from '../model/useSynthesis';
import SummaryBlock from './SummaryBlock';

// OpenAI's raw statuses read as jargon on screen ("in_progress").
const BATCH_STATUS_LABELS = {
  validating: 'en validation',
  in_progress: 'en cours de traitement',
  finalizing: 'en finalisation',
};

const isGlobal = summary => summary.section_id === null || summary.section_id === undefined;

/** Where the OpenAI batch stands, and its cancellation while it runs. */
const BatchBanner = ({ batch, pending, cancelling, onCancel }) => {
  let tone = 'alert-error';
  if (pending) tone = 'alert-info';
  else if (batch.status === 'collected') tone = 'alert-success';

  let text;
  if (batch.status === 'cancelling') {
    text = 'Annulation en cours… Les boutons se réactiveront dès qu’OpenAI l’aura confirmée.';
  } else if (pending) {
    // No count before OpenAI has one: validation used to show "0/0".
    const count =
      batch.total > 0 ? ` — ${batch.completed ?? 0}/${batch.total} résumés de section` : '';
    text =
      `Batch ${BATCH_STATUS_LABELS[batch.status] || batch.status}${count}. Le résultat peut prendre ` +
      'jusqu’à 24 h ; cette page se met à jour toute seule, et rien n’est perdu si tu la quittes.';
  } else if (batch.status === 'cancelled') {
    text = 'Batch annulé : aucun résumé n’a été produit. Tu peux relancer la synthèse.';
  } else if (batch.status === 'collected') {
    const sections = typeof batch.sections === 'number' ? ` (${batch.sections} sections)` : '';
    text = `Résumés de section produits en batch${sections}, synthèse générée.`;
  } else {
    text = `Batch terminé sans résultat (${batch.status})${batch.message ? ` — ${batch.message}` : ''}.`;
  }

  return (
    <div className={`alert flex items-start justify-between gap-4 ${tone}`}>
      <div>{text}</div>
      {/* Hidden once cancelling: a second request would only be refused. */}
      {pending && batch.status !== 'cancelling' && (
        <Button onClick={onCancel} variant="danger" size="sm" disabled={cancelling}>
          {cancelling ? 'Annulation…' : 'Annuler le batch'}
        </Button>
      )}
    </div>
  );
};

/** The synthesis of one DD type: per-section summaries and a global one. */
const SynthesisTab = ({ sessionId, ddTypeCode, ddTypeName }) => {
  const synthesis = useSynthesis(sessionId, ddTypeCode);
  const { summaries, batch, batchPending, generating } = synthesis;

  // The synthesis is strictly per DD type.
  if (!ddTypeCode) {
    return (
      <div className={`${panel.base} ${emptyState.wrapper}`}>
        <DocumentTextIcon className={emptyState.icon} />
        <h3 className={emptyState.title}>Sélectionne un type de DD</h3>
        <p className={emptyState.text}>
          La synthèse se génère par type de DD. Ouvre la revue pour un type de DD précis pour
          générer ou consulter sa synthèse.
        </p>
      </div>
    );
  }

  const global = summaries.find(isGlobal);
  const sectionSummaries = summaries.filter(summary => !isGlobal(summary));

  return (
    <div className="space-y-6 pb-12">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium text-content">
            Synthèse — {ddTypeName || ddTypeCode}
          </h2>
          <p className="text-sm text-content-muted">
            Résumé par section + synthèse globale (repris dans le PDF). Basé sur les réponses
            actuelles.
          </p>
        </div>
        {/* While OpenAI still holds the job, neither path may be relaunched: the
            backend refuses a second submission, and a synchronous run would be
            overwritten by the batch landing behind it. */}
        <div className="flex items-center gap-3">
          <Button
            onClick={synthesis.generate}
            variant="primary"
            icon={ArrowPathRoundedSquareIcon}
            disabled={generating || batchPending}
          >
            {generating
              ? 'Génération…'
              : summaries.length > 0
                ? 'Régénérer la synthèse'
                : 'Générer la synthèse'}
          </Button>
          {/* Same result at half price, but OpenAI has up to 24h to deliver it.
              Secondary on purpose: the immediate path stays the obvious one. */}
          <Button
            onClick={synthesis.generateBatch}
            variant="secondary"
            icon={ClockIcon}
            disabled={generating || batchPending}
            title="Passe par l’API Batch d’OpenAI : moitié prix, mais le résultat peut mettre jusqu’à 24 h."
          >
            Générer en batch (−50 %)
          </Button>
        </div>
      </div>

      {batch && (
        <BatchBanner
          batch={batch}
          pending={batchPending}
          cancelling={synthesis.cancellingBatch}
          onCancel={synthesis.cancelBatch}
        />
      )}

      {synthesis.loading ? (
        <div className="py-12 flex justify-center">
          <LoadingSpinner size="lg" text="Chargement de la synthèse…" />
        </div>
      ) : summaries.length === 0 ? (
        <div className={`${emptyState.wrapper} border-2 border-dashed border-border rounded-lg`}>
          <DocumentTextIcon className={emptyState.icon} />
          <h3 className={emptyState.title}>Aucune synthèse pour le moment</h3>
          <p className={emptyState.text}>
            Clique sur « Générer la synthèse » pour la créer à partir des réponses actuelles.
          </p>
        </div>
      ) : (
        <>
          {global && (
            <SummaryBlock title="Synthèse globale" summary={global} onSaved={synthesis.load} />
          )}
          {sectionSummaries.length > 0 && (
            <div className="space-y-4">
              <h3 className="eyebrow">Résumés par section</h3>
              {sectionSummaries.map(summary => (
                <SummaryBlock
                  key={summary.id}
                  title={summary.section_title || 'Section'}
                  summary={summary}
                  onSaved={synthesis.load}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default SynthesisTab;
