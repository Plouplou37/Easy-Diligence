"""
Summary generation for due diligence reports.

Produces, per DD type of a session:
  - one summary per section (from that section's current answers)
  - one overall DD-type synthesis (from the section summaries)

The content is already retrieved (the answers), so generation uses plain text
LLM calls with NO tools (no file_search / web_search).

Two paths share the same prompts and the same request body:
  - synchronous (generate_summaries_for_dd_type): section summaries are
    generated concurrently, then the synthesis. Immediate, full price.
  - Batch (submit_section_summaries_batch / collect_section_summaries_batch):
    the section summaries go through the Batch API at half price. Its only
    completion window is 24h, and the synthesis consumes the section summaries,
    so batching it too would chain a second 24h window: only stage 1 is batched
    and the final synthesis stays a synchronous call made at collection time.
"""

import asyncio
import logging

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, InvalidRequestError, NotFoundError
from app.engine.openai_client import OpenAIProcessor
from app.models.answer import AnswerStatus, DDAnswer
from app.models.dd_types import DDType
from app.models.questions import DDQuestion, DDSection
from app.models.summary import DDSummary, DDSummaryBatch

logger = logging.getLogger(__name__)


SECTION_SYSTEM_PROMPT = (
    "Tu es un analyste expert en due diligence. À partir des questions et de leurs "
    "réponses pour une section, rédige un résumé synthétique, factuel et concis "
    "(quelques paragraphes) : constats clés, forces et points d'attention/risques. "
    "N'invente aucune information : appuie-toi uniquement sur les réponses fournies."
)

SYNTHESIS_SYSTEM_PROMPT = (
    "Tu es un analyste expert en due diligence. À partir des résumés de section "
    "fournis, rédige une SYNTHÈSE structurée et complète mais concise (environ 3 à 4 "
    "pages, ~1500-2000 mots maximum) destinée à un comité d'investissement. "
    "Structure attendue : une courte introduction, les points clés regroupés par thème, "
    "les forces, les risques et points d'attention, puis une conclusion / recommandation. "
    "Style professionnel et factuel. N'invente rien : appuie-toi uniquement sur les résumés fournis.\n\n"
    "FORMAT (markdown, important pour la mise en page du PDF) :\n"
    "- Utilise des titres de niveau 2 « ## » pour les grandes parties "
    "(## Introduction, ## Points clés, ## Forces, ## Risques et points d'attention, "
    "## Conclusion et recommandation).\n"
    "- Utilise des sous-titres « ### » pour les thèmes à l'intérieur d'une partie.\n"
    "- Utilise des listes à puces « - » pour énumérer forces, risques et constats.\n"
    "- Mets en gras « **…** » les termes importants. Évite les pavés de texte trop longs."
)

SECTION_MAX_OUTPUT_TOKENS = 2500
SYNTHESIS_MAX_OUTPUT_TOKENS = 6000

# Prefix of the Batch custom_id. Output lines come back in an arbitrary order,
# so the section id has to travel with the request rather than its position.
_CUSTOM_ID_PREFIX = "section-"

# States in which the job is still with OpenAI and must not be resubmitted.
PENDING_BATCH_STATUSES = {"validating", "in_progress", "finalizing", "cancelling"}
# States from which nothing will ever come back.
DEAD_BATCH_STATUSES = {"failed", "expired", "cancelled"}


def _company_name(session) -> str:
    return session.company.name if getattr(session, "company", None) else "la société cible"


def _custom_id_for(section_id: int) -> str:
    return f"{_CUSTOM_ID_PREFIX}{section_id}"


def _upsert_summary(
    db: Session, session_id: int, dd_type_id: int, section_id, text: str
) -> DDSummary:
    """Create or overwrite the current summary for a (session, dd_type, section) scope."""
    existing = (
        db.query(DDSummary)
        .filter(
            DDSummary.session_id == session_id,
            DDSummary.dd_type_id == dd_type_id,
            DDSummary.section_id == section_id,
        )
        .first()
    )
    if existing:
        existing.summary_text = text
        existing.edited_by = None  # regenerated -> back to AI-generated
        return existing
    summary = DDSummary(
        session_id=session_id,
        dd_type_id=dd_type_id,
        section_id=section_id,
        summary_text=text,
    )
    db.add(summary)
    return summary


def _load_sections_with_answers(db: Session, session, dd_type_code: str):
    """Resolve the DD type and group its current answers by section, in order.

    Returns (dd_type_obj, [(section, [answers])]).
    Raises ValueError if the DD type is unknown or has no current answers.
    """
    dd_type_obj = db.query(DDType).filter(DDType.code == dd_type_code).first()
    if not dd_type_obj:
        raise NotFoundError(f"DD type with code '{dd_type_code}' not found")

    # Current answers for this session + DD type, joined to section/question, ordered
    answers = (
        db.query(DDAnswer)
        .join(DDSection, DDAnswer.section_id == DDSection.id)
        .join(DDQuestion, DDAnswer.question_id == DDQuestion.id)
        .filter(
            DDAnswer.session_id == session.id,
            DDAnswer.dd_type_id == dd_type_obj.id,
            DDAnswer.is_current == True,
            DDAnswer.status != AnswerStatus.FAILED,
        )
        .order_by(DDSection.order_index, DDQuestion.order_index)
        .all()
    )

    if not answers:
        raise InvalidRequestError("No current answers found for this session and DD type")

    # Group answers by section (preserve order)
    sections = []  # list of (section_obj, [answers])
    by_section_id = {}
    for ans in answers:
        sid = ans.section_id
        if sid not in by_section_id:
            bucket = []
            by_section_id[sid] = bucket
            sections.append((ans.section, bucket))
        by_section_id[sid].append(ans)

    return dd_type_obj, sections


def _build_section_user_prompt(company: str, section, section_answers) -> str:
    title = section.title if section and section.title else "Section"
    lines = [f"Société : {company}", f"Section : {title}", ""]
    for ans in section_answers:
        q = ans.question.question_text if ans.question else (ans.question_code or "Question")
        a = ans.answer_text or "(pas de réponse)"
        lines.append(f"Q : {q}")
        lines.append(f"R : {a}")
        lines.append("")
    lines.append("Rédige le résumé synthétique de cette section.")
    return "\n".join(lines)


def _build_synthesis_user_prompt(company: str, dd_type_obj, section_summary_pairs) -> str:
    lines = [f"Société : {company}", f"Dossier de due diligence : {dd_type_obj.name}", ""]
    for section, text in section_summary_pairs:
        title = section.title if section and section.title else "Section"
        lines.append(f"## {title}")
        lines.append(text)
        lines.append("")
    lines.append("Rédige la synthèse globale de ce dossier de due diligence.")
    return "\n".join(lines)


async def _generate_and_upsert_synthesis(
    db: Session,
    session,
    dd_type_obj,
    company: str,
    section_summary_pairs,
    processor: OpenAIProcessor,
) -> DDSummary | None:
    """Build the DD-type synthesis from the section summaries and store it.

    Always synchronous, on both paths: it consumes the section summaries, so it
    cannot be enqueued alongside them.
    """
    if not section_summary_pairs:
        return None

    synthesis_user_prompt = _build_synthesis_user_prompt(
        company, dd_type_obj, section_summary_pairs
    )
    synthesis_text = await asyncio.to_thread(
        processor.generate_summary,
        SYNTHESIS_SYSTEM_PROMPT,
        synthesis_user_prompt,
        SYNTHESIS_MAX_OUTPUT_TOKENS,
    )
    synthesis_text = (synthesis_text or "").strip()
    if not synthesis_text:
        return None

    synthesis_row = _upsert_summary(db, session.id, dd_type_obj.id, None, synthesis_text)
    db.commit()
    return synthesis_row


async def generate_summaries_for_dd_type(
    db: Session, session, dd_type_code: str
) -> list[DDSummary]:
    """Generate (and persist) section summaries + the DD-type synthesis.

    Synchronous path: everything is produced within the request. Returns the list
    of upserted DDSummary rows (sections first, synthesis last).
    Raises ValueError if the DD type is unknown or has no current answers.
    """
    dd_type_obj, sections = _load_sections_with_answers(db, session, dd_type_code)
    company = _company_name(session)
    processor = OpenAIProcessor()

    # --- Section summaries (concurrent) -------------------------------------
    section_prompts = [
        (section, _build_section_user_prompt(company, section, section_answers))
        for section, section_answers in sections
    ]

    section_texts = await asyncio.gather(
        *[
            asyncio.to_thread(
                processor.generate_summary,
                SECTION_SYSTEM_PROMPT,
                user_prompt,
                SECTION_MAX_OUTPUT_TOKENS,
            )
            for _, user_prompt in section_prompts
        ]
    )

    upserted: list[DDSummary] = []
    section_summary_pairs = []  # (section, text) for synthesis prompt
    for (section, _), text in zip(section_prompts, section_texts, strict=False):
        text = (text or "").strip()
        if not text:
            continue
        upserted.append(_upsert_summary(db, session.id, dd_type_obj.id, section.id, text))
        section_summary_pairs.append((section, text))

    db.commit()

    # --- DD-type synthesis (single call from the section summaries) ----------
    synthesis_row = await _generate_and_upsert_synthesis(
        db, session, dd_type_obj, company, section_summary_pairs, processor
    )
    if synthesis_row is not None:
        upserted.append(synthesis_row)

    for row in upserted:
        db.refresh(row)
    return upserted


# === Batch path ============================================================


def submit_section_summaries_batch(
    db: Session, session, dd_type_code: str, user_id: int | None = None
) -> DDSummaryBatch:
    """Enqueue the section summaries of a (session, DD type) as an OpenAI batch.

    Returns the tracking row. The synthesis is NOT enqueued: it is produced when
    the batch is collected. Raises ValueError if a batch is already pending for
    this scope, or if the DD type is unknown / has no current answers.
    """
    dd_type_obj, sections = _load_sections_with_answers(db, session, dd_type_code)
    company = _company_name(session)

    existing = (
        db.query(DDSummaryBatch)
        .filter(
            DDSummaryBatch.session_id == session.id,
            DDSummaryBatch.dd_type_id == dd_type_obj.id,
        )
        .first()
    )
    if existing and existing.status in PENDING_BATCH_STATUSES:
        raise ConflictError(
            f"A summary batch is already running for this DD type (status: {existing.status})"
        )

    processor = OpenAIProcessor()
    requests = [
        {
            "custom_id": _custom_id_for(section.id),
            "body": processor.build_summary_request_params(
                SECTION_SYSTEM_PROMPT,
                _build_section_user_prompt(company, section, section_answers),
                SECTION_MAX_OUTPUT_TOKENS,
            ),
        }
        for section, section_answers in sections
    ]

    submitted = processor.submit_summary_batch(
        requests, description=f"{company} / {dd_type_obj.code} section summaries"
    )

    # One row per (session, dd_type): relaunching replaces the finished job.
    row = existing or DDSummaryBatch(session_id=session.id, dd_type_id=dd_type_obj.id)
    row.openai_batch_id = submitted["batch_id"]
    row.input_file_id = submitted["input_file_id"]
    row.output_file_id = None
    row.status = submitted["status"]
    row.error_message = None
    row.created_by = user_id
    if existing is None:
        db.add(row)
    db.commit()
    db.refresh(row)

    logger.info(
        f"Queued {len(requests)} section summaries for session {session.id} / "
        f"{dd_type_obj.code} as batch {row.openai_batch_id}"
    )
    return row


async def collect_section_summaries_batch(
    db: Session, session, dd_type_code: str
) -> tuple[DDSummaryBatch | None, dict]:
    """Refresh a batch's state and, once complete, store its results.

    On completion: the section summaries are stored, then the synthesis is
    generated synchronously from them. Idempotent -- a batch already collected
    is reported as such without regenerating anything.

    Returns (row, info) where info describes the state to the caller.
    """
    dd_type_obj = db.query(DDType).filter(DDType.code == dd_type_code).first()
    if not dd_type_obj:
        raise NotFoundError(f"DD type with code '{dd_type_code}' not found")

    row = (
        db.query(DDSummaryBatch)
        .filter(
            DDSummaryBatch.session_id == session.id,
            DDSummaryBatch.dd_type_id == dd_type_obj.id,
        )
        .first()
    )
    if not row:
        return None, {"status": "none", "message": "No summary batch for this DD type"}

    if row.status == "collected":
        return row, {"status": "collected", "message": "Results already stored"}

    processor = OpenAIProcessor()
    state = processor.get_batch(row.openai_batch_id)

    row.status = state["status"]
    row.output_file_id = state.get("output_file_id")

    if state["status"] in DEAD_BATCH_STATUSES:
        row.error_message = f"Batch ended with status '{state['status']}'"
        db.commit()
        return row, {"status": state["status"], "message": row.error_message}

    if state["status"] != "completed":
        db.commit()
        return row, {
            "status": state["status"],
            "completed": state.get("completed"),
            "total": state.get("total"),
            "message": "Batch still running",
        }

    if not row.output_file_id:
        row.error_message = "Batch completed without an output file"
        db.commit()
        return row, {"status": "failed", "message": row.error_message}

    # --- Completed: store the section summaries -----------------------------
    texts = processor.fetch_batch_texts(row.output_file_id)

    # Reload the sections so the synthesis prompt keeps the questionnaire order,
    # which the batch output does not preserve.
    _, sections = _load_sections_with_answers(db, session, dd_type_code)
    company = _company_name(session)

    section_summary_pairs = []
    for section, _answers in sections:
        text = (texts.get(_custom_id_for(section.id)) or "").strip()
        if not text:
            continue
        _upsert_summary(db, session.id, dd_type_obj.id, section.id, text)
        section_summary_pairs.append((section, text))

    db.commit()

    if not section_summary_pairs:
        row.error_message = "Batch completed but returned no usable summary"
        db.commit()
        return row, {"status": "failed", "message": row.error_message}

    # --- Then the synthesis, synchronously ----------------------------------
    await _generate_and_upsert_synthesis(
        db, session, dd_type_obj, company, section_summary_pairs, processor
    )

    row.status = "collected"
    row.error_message = None
    db.commit()
    db.refresh(row)

    logger.info(
        f"Collected batch {row.openai_batch_id}: {len(section_summary_pairs)} "
        f"section summaries + synthesis for session {session.id} / {dd_type_obj.code}"
    )
    return row, {
        "status": "collected",
        "sections": len(section_summary_pairs),
        "message": "Summaries stored",
    }


def cancel_section_summaries_batch(
    db: Session, session, dd_type_code: str
) -> tuple[DDSummaryBatch | None, dict]:
    """Cancel the pending section-summaries batch of a (session, DD type).

    The state is refreshed from OpenAI first. The stored status only moves when
    somebody polls, so it can still read 'in_progress' for a batch that has
    meanwhile completed -- and cancelling that one would throw away results
    already paid for. Only a batch OpenAI itself reports as running is cancelled.

    Returns (row, info), like collect_section_summaries_batch.
    """
    dd_type_obj = db.query(DDType).filter(DDType.code == dd_type_code).first()
    if not dd_type_obj:
        raise NotFoundError(f"DD type with code '{dd_type_code}' not found")

    row = (
        db.query(DDSummaryBatch)
        .filter(
            DDSummaryBatch.session_id == session.id,
            DDSummaryBatch.dd_type_id == dd_type_obj.id,
        )
        .first()
    )
    if not row:
        raise NotFoundError("No summary batch for this DD type")

    if row.status == "collected":
        return row, {"status": "collected", "message": "Batch already collected, nothing to cancel"}

    processor = OpenAIProcessor()
    state = processor.get_batch(row.openai_batch_id)
    row.status = state["status"]
    row.output_file_id = state.get("output_file_id")

    if state["status"] == "cancelling":
        db.commit()
        return row, {"status": "cancelling", "message": "Cancellation already in progress"}

    if state["status"] not in PENDING_BATCH_STATUSES:
        # Completed, failed, expired or already cancelled: nothing left to stop.
        # A completed batch is collected by the next status call, as usual.
        db.commit()
        return row, {
            "status": state["status"],
            "message": f"Batch is no longer running (status: {state['status']})",
        }

    cancelled = processor.cancel_batch(row.openai_batch_id)
    row.status = cancelled["status"]
    db.commit()
    db.refresh(row)

    logger.info(
        f"Cancel requested for batch {row.openai_batch_id} "
        f"(session {session.id} / {dd_type_obj.code}), status={row.status}"
    )
    return row, {
        "status": row.status,
        "completed": cancelled.get("completed"),
        "total": cancelled.get("total"),
        "message": "Cancellation requested",
    }
