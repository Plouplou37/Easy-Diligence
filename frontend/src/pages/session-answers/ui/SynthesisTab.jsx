import React, { useState, useEffect, useCallback, useRef } from 'react';
import { ArrowPathRoundedSquareIcon, PencilIcon, CheckIcon, XMarkIcon, DocumentTextIcon, ClockIcon } from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import toast from 'react-hot-toast';
import { summariesAPI } from '@/entities/summary';
import { Button, LoadingSpinner, emptyState, panel, sectionHeader } from '@/shared/ui';

// One editable block (the global synthesis or a section summary).
const SummaryBlock = ({ title, summary, onSaved }) => {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(summary.summary_text || '');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!editing) setText(summary.summary_text || '');
  }, [summary.summary_text, editing]);

  const save = async () => {
    setSaving(true);
    try {
      await summariesAPI.update(summary.id, text);
      setEditing(false);
      toast.success('Résumé enregistré.');
      onSaved?.();
    } catch (e) {
      console.error('Failed to save summary:', e);
      toast.error("Échec de l'enregistrement.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={`${panel.base} p-5`}>
      <div className="flex items-center justify-between gap-3 mb-3">
        <h3 className="text-fluid-sm font-medium text-content uppercase tracking-[0.18em]">{title}</h3>
        <div className={sectionHeader.hairline} />
        {!editing && (
          <Button onClick={() => setEditing(true)} variant="secondary" size="sm" icon={PencilIcon}>
            Éditer
          </Button>
        )}
      </div>

      {editing ? (
        <div className="space-y-3">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={14}
            className="form-input w-full px-3 py-2 text-sm font-mono"
          />
          <div className="flex space-x-2">
            <Button onClick={save} variant="success" icon={CheckIcon} disabled={saving}>
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </Button>
            <Button onClick={() => setEditing(false)} variant="secondary" icon={XMarkIcon} disabled={saving}>
              Annuler
            </Button>
          </div>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <div className="prose prose-sm max-w-none text-sm text-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {summary.summary_text || '_(vide)_'}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
};

// A batch still in OpenAI's hands. Mirrors PENDING_BATCH_STATUSES in
// engine/summarizer.py -- while the status is one of these, nothing is stored yet.
const PENDING_BATCH_STATUSES = ['validating', 'in_progress', 'finalizing', 'cancelling'];

// OpenAI's raw statuses read as jargon on screen ("in_progress").
const BATCH_STATUS_LABELS = {
  validating: 'en validation',
  in_progress: 'en cours de traitement',
  finalizing: 'en finalisation',
};

const SynthesisTab = ({ sessionId, ddTypeCode, ddTypeName }) => {
  const [summaries, setSummaries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  // State of the OpenAI batch, when one was launched for this DD type.
  const [batch, setBatch] = useState(null);
  const [cancellingBatch, setCancellingBatch] = useState(false);
  const previousBatchStatus = useRef(null);

  const load = useCallback(async () => {
    if (!ddTypeCode) return;
    setLoading(true);
    try {
      const res = await summariesAPI.list(sessionId, ddTypeCode);
      setSummaries(Array.isArray(res.data) ? res.data : []);
    } catch (e) {
      console.error('Failed to load summaries:', e);
      toast.error('Échec du chargement de la synthèse.');
    } finally {
      setLoading(false);
    }
  }, [sessionId, ddTypeCode]);

  useEffect(() => { load(); }, [load]);

  // Polling the status is also what collects a finished batch server-side, so
  // this is not merely reading state: it is what turns results into summaries.
  const refreshBatch = useCallback(async () => {
    if (!ddTypeCode) return null;
    try {
      const res = await summariesAPI.batchStatus(sessionId, ddTypeCode);
      const state = res.data || null;
      setBatch(state && state.status !== 'none' ? state : null);

      // Announce the transition only, not the steady state: a batch collected
      // during an earlier visit must not toast on every mount.
      const was = previousBatchStatus.current;
      previousBatchStatus.current = state?.status || null;
      if (state?.status === 'collected' && PENDING_BATCH_STATUSES.includes(was)) {
        await load();
        toast.success('Synthèse générée (batch).');
      }
      return state;
    } catch (e) {
      console.error('Failed to read batch status:', e);
      return null;
    }
  }, [sessionId, ddTypeCode, load]);

  // Pick up a batch left running by a previous visit -- it survives a reload,
  // and a page refresh is otherwise the only thing that would advance it.
  useEffect(() => {
    previousBatchStatus.current = null;
    refreshBatch();
  }, [refreshBatch]);

  // Keep polling while OpenAI still has the job.
  useEffect(() => {
    if (!batch || !PENDING_BATCH_STATUSES.includes(batch.status)) return undefined;
    const interval = setInterval(refreshBatch, 15000);
    return () => clearInterval(interval);
  }, [batch, refreshBatch]);

  const handleGenerate = async () => {
    if (!ddTypeCode) return;
    setGenerating(true);
    try {
      await summariesAPI.generate(sessionId, ddTypeCode);
      await load();
      toast.success('Synthèse générée.');
    } catch (e) {
      console.error('Failed to generate synthesis:', e);
      const detail = e?.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail : 'Échec de la génération de la synthèse.';
      toast.error(msg);
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerateBatch = async () => {
    if (!ddTypeCode) return;
    setGenerating(true);
    try {
      const res = await summariesAPI.generateBatch(sessionId, ddTypeCode);
      setBatch(res.data || null);
      previousBatchStatus.current = res.data?.status || null;
      toast.success('Résumés de section mis en file (batch).');
    } catch (e) {
      console.error('Failed to queue synthesis batch:', e);
      const detail = e?.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail : 'Échec de la mise en file du batch.';
      toast.error(msg);
    } finally {
      setGenerating(false);
    }
  };

  const handleCancelBatch = async () => {
    if (!ddTypeCode) return;
    // Irreversible: the requests not yet processed are dropped for good.
    if (!window.confirm('Annuler le batch ? Les résumés pas encore produits seront abandonnés.')) return;
    setCancellingBatch(true);
    try {
      const res = await summariesAPI.cancelBatch(sessionId, ddTypeCode);
      const state = res.data || null;
      if (state && PENDING_BATCH_STATUSES.includes(state.status)) {
        // 'cancelling': keep polling until OpenAI confirms 'cancelled'.
        setBatch(state);
        previousBatchStatus.current = state.status;
        toast.success('Annulation demandée.');
      } else {
        // Already over on OpenAI's side. Let the regular status call record it
        // -- and collect the results, if it turns out to have completed.
        previousBatchStatus.current = 'in_progress';
        await refreshBatch();
        toast(state?.message || 'Le batch était déjà terminé.');
      }
    } catch (e) {
      console.error('Failed to cancel synthesis batch:', e);
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : "Échec de l'annulation du batch.");
    } finally {
      setCancellingBatch(false);
    }
  };

  // No DD type in context -> guide the user (synthesis is strictly per DD type).
  if (!ddTypeCode) {
    return (
      <div className={`${panel.base} ${emptyState.wrapper}`}>
        <DocumentTextIcon className={emptyState.icon} />
        <h3 className={emptyState.title}>
          Sélectionne un type de DD
        </h3>
        <p className={emptyState.text}>
          La synthèse se génère par type de DD. Ouvre la revue pour un type de DD précis
          pour générer ou consulter sa synthèse.
        </p>
      </div>
    );
  }

  const synthesis = summaries.find((s) => s.section_id === null || s.section_id === undefined);
  const sectionSummaries = summaries.filter((s) => s.section_id !== null && s.section_id !== undefined);
  // While OpenAI still holds the job, neither path may be relaunched: the
  // backend refuses a second submission, and a synchronous run would be
  // overwritten by the batch landing behind it.
  const batchPending = !!batch && PENDING_BATCH_STATUSES.includes(batch.status);

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
        <div className="flex items-center gap-3">
          <Button onClick={handleGenerate} variant="primary" icon={ArrowPathRoundedSquareIcon}
            disabled={generating || batchPending}>
            {generating
              ? 'Génération…'
              : (summaries.length > 0 ? 'Régénérer la synthèse' : 'Générer la synthèse')}
          </Button>
          {/* Same result at half price, but OpenAI has up to 24h to deliver it.
              Secondary on purpose: the immediate path stays the obvious one. */}
          <Button onClick={handleGenerateBatch} variant="secondary" icon={ClockIcon}
            disabled={generating || batchPending}
            title="Passe par l'API Batch d'OpenAI : moitié prix, mais le résultat peut mettre jusqu'à 24 h.">
            Générer en batch (−50 %)
          </Button>
        </div>
      </div>

      {batch && batch.status !== 'none' && (
        <div className={`alert flex items-start justify-between gap-4 ${batchPending
          ? 'alert-info'
          : batch.status === 'collected'
            ? 'alert-success'
            : 'alert-error'}`}>
          <div>
          {batch.status === 'cancelling' ? (
            <>Annulation en cours… Les boutons se réactiveront dès qu'OpenAI l'aura confirmée.</>
          ) : batchPending ? (
            <>
              Batch {BATCH_STATUS_LABELS[batch.status] || batch.status}
              {/* No count before OpenAI has one: validation used to show "0/0". */}
              {batch.total > 0 && ` — ${batch.completed ?? 0}/${batch.total} résumés de section`}
              . Le résultat peut prendre jusqu'à 24 h ; cette page se met à jour toute seule,
              et rien n'est perdu si tu la quittes.
            </>
          ) : batch.status === 'cancelled' ? (
            <>Batch annulé : aucun résumé n'a été produit. Tu peux relancer la synthèse.</>
          ) : batch.status === 'collected' ? (
            <>
              Résumés de section produits en batch
              {typeof batch.sections === 'number' && ` (${batch.sections} sections)`}
              , synthèse générée.
            </>
          ) : (
            <>Batch terminé sans résultat ({batch.status}){batch.message ? ` — ${batch.message}` : ''}.</>
          )}
          </div>
          {/* Hidden once cancelling: a second request would only be refused. */}
          {batchPending && batch.status !== 'cancelling' && (
            <Button onClick={handleCancelBatch} variant="danger" size="sm" disabled={cancellingBatch}>
              {cancellingBatch ? 'Annulation…' : 'Annuler le batch'}
            </Button>
          )}
        </div>
      )}

      {loading ? (
        <div className="py-12 flex justify-center">
          <LoadingSpinner size="lg" text="Chargement de la synthèse…" />
        </div>
      ) : summaries.length === 0 ? (
        <div className={`${emptyState.wrapper} border-2 border-dashed border-border rounded-lg`}>
          <DocumentTextIcon className={emptyState.icon} />
          <h3 className={emptyState.title}>
            Aucune synthèse pour le moment
          </h3>
          <p className={emptyState.text}>
            Clique sur « Générer la synthèse » pour la créer à partir des réponses actuelles.
          </p>
        </div>
      ) : (
        <>
          {synthesis && (
            <SummaryBlock title="Synthèse globale" summary={synthesis} onSaved={load} />
          )}

          {sectionSummaries.length > 0 && (
            <div className="space-y-4">
              <h3 className="eyebrow">
                Résumés par section
              </h3>
              {sectionSummaries.map((s) => (
                <SummaryBlock
                  key={s.id}
                  title={s.section_title || 'Section'}
                  summary={s}
                  onSaved={load}
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
