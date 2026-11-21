"""The session report, as a PDF.

The body is the synthesis of each DD type; the annex gives, section by section,
its summary, then every question with its answer and sources. Without a
synthesis, the report is the detail alone. The colours, the footer notice and
the optional banner come from the configuration (PDF_*, BRAND_BANNER_PATH).
"""

import io
import logging
import os
import re
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import settings
from app.exports.markdown import esc, markdown_to_flowables, spaced_caps
from app.exports.sources import format_sources
from app.models.answer import DDAnswer
from app.models.session import DDSession
from app.models.summary import DDSummary
from app.services.question_codes import reference_of

logger = logging.getLogger(__name__)

MEDIA_TYPE = "application/pdf"


def report_filename(session: DDSession) -> str:
    """The report's file name: the session's, spaces made underscores."""
    name = (session.name or f"session-{session.id}").replace(" ", "_")
    return f"{name}_DD_Report.pdf"


def _banner_path() -> str | None:
    """Path of the optional banner (BRAND_BANNER_PATH), or None.

    Unset means no banner. Set but missing (an optional volume that was not
    mounted) logs a warning, and the report is produced without it.
    """
    path = settings.brand_banner_path
    if not path:
        return None
    if not os.path.isfile(path):
        logger.warning("BRAND_BANNER_PATH points to a missing file: %s", path)
        return None
    return path


def _logo_size(path: str | None, max_width: float) -> tuple[float, float] | None:
    """(width, height) of the banner scaled to max_width, or None."""
    if not path:
        return None
    try:
        image_width, image_height = ImageReader(path).getSize()
        return max_width, max_width * image_height / image_width
    except Exception:
        logger.warning("Unreadable PDF banner, exported without it: %s", path)
        return None


# A reference ("A.01") at the head of a question text, as older texts still have.
_TEXT_REFERENCE = re.compile(r"^\s*[A-Za-z]{1,3}\.?\d{1,3}\s*-\s")


def _question_text(answer: DDAnswer) -> str:
    """Question text lives on the related DDQuestion, not on DDAnswer.

    The reference ("A.01 - ") used to open the text itself; it now lives in the
    question code only. A report read by a committee still needs the numbering,
    so it is put back in front -- unless the text already opens with one, as it
    does for rows that predate the move.
    """
    question = getattr(answer, "question", None)
    if question is not None and getattr(question, "question_text", None):
        text = question.question_text
        reference = reference_of(answer.question_code)
        if reference and not _TEXT_REFERENCE.match(text):
            return f"{reference} - {text}"
        return text
    return answer.question_code or "No question text"


def _section_title(answer: DDAnswer) -> str:
    """Prefer the DDSection title, falling back to the legacy section_code."""
    section = getattr(answer, "section", None)
    if section is not None and getattr(section, "title", None):
        return section.title
    return answer.section_code or "General"


def build_report(
    session: DDSession, answers: list[DDAnswer], summaries: list[DDSummary] | None = None
) -> bytes:
    """Generate a branded PDF report for session answers.

    When ``summaries`` is provided, the report leads with a per-DD-type
    synthesis (the readable body) and pushes the question/answer/source
    detail into an annex (each section prefixed by its summary). When no
    summaries exist, it falls back to the original detail-only layout.
    """
    buffer = io.BytesIO()
    primary = colors.HexColor(settings.pdf_primary_color)
    secondary = colors.HexColor(settings.pdf_text_color)
    rule = colors.HexColor(settings.pdf_rule_color)

    company_name = session.company.name if session.company else "N/A"

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,  # ~0.7in sides
        topMargin=54,
        bottomMargin=44,  # leaves room for the running header/footer
        title=f"Due Diligence Report - {company_name}",
        author=settings.app_name,
    )
    banner = _banner_path()

    # --- Styles -------------------------------------------------------
    styles = getSampleStyleSheet()
    label_style = ParagraphStyle(
        "BrandLabel",
        parent=styles["Normal"],
        fontSize=12,
        textColor=primary,
        alignment=TA_CENTER,
        spaceAfter=6,
        leading=18,
    )
    cover_company_style = ParagraphStyle(
        "CoverCompany",
        parent=styles["Heading1"],
        fontSize=26,
        textColor=primary,
        alignment=TA_CENTER,
        spaceBefore=10,
        spaceAfter=6,
        leading=30,
    )
    cover_meta_style = ParagraphStyle(
        "CoverMeta",
        parent=styles["Normal"],
        fontSize=10,
        textColor=secondary,
        alignment=TA_CENTER,
        leading=14,
    )
    ddtype_style = ParagraphStyle(
        "DDType",
        parent=styles["Heading1"],
        fontSize=17,
        textColor=primary,
        spaceBefore=4,
        spaceAfter=6,
        leading=21,
    )
    section_style = ParagraphStyle(
        "SectionBar",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.white,
        leading=15,
        fontName="Helvetica-Bold",
    )
    question_style = ParagraphStyle(
        "Question",
        parent=styles["Normal"],
        fontSize=11,
        textColor=primary,
        fontName="Helvetica-Oblique",
        spaceBefore=2,
        spaceAfter=3,
        leading=15,
        keepWithNext=1,  # italic, never orphaned
    )
    answer_style = ParagraphStyle(
        "Answer",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#1A1A1A"),
        alignment=TA_JUSTIFY,
        spaceAfter=4,
        leading=14,
    )
    source_label_style = ParagraphStyle(
        "SourceLabel",
        parent=styles["Normal"],
        fontSize=7,
        textColor=primary,
        leading=11,
        spaceBefore=2,
        spaceAfter=1,
    )
    source_style = ParagraphStyle(
        "Source",
        parent=styles["Normal"],
        fontSize=8,
        textColor=secondary,
        leading=11,
        leftIndent=10,
    )
    synthesis_style = ParagraphStyle(
        "Synthesis",
        parent=styles["Normal"],
        fontSize=10.5,
        textColor=colors.HexColor("#1A1A1A"),
        alignment=TA_JUSTIFY,
        spaceAfter=8,
        leading=16,
    )
    annex_title_style = ParagraphStyle(
        "AnnexTitle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=primary,
        alignment=TA_CENTER,
        spaceBefore=10,
        spaceAfter=10,
        leading=24,
    )
    section_summary_style = ParagraphStyle(
        "SectionSummary",
        parent=styles["Normal"],
        fontSize=9.5,
        textColor=secondary,
        alignment=TA_JUSTIFY,
        spaceBefore=4,
        spaceAfter=8,
        leading=14,
        fontName="Helvetica-Oblique",
    )

    # --- Heading / bullet styles for structured markdown content ------
    synth_h1_style = ParagraphStyle(
        "SynthH1",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=primary,
        fontName="Helvetica-Bold",
        spaceBefore=14,
        spaceAfter=5,
        leading=18,
        keepWithNext=1,
    )
    synth_h2_style = ParagraphStyle(
        "SynthH2",
        parent=styles["Heading3"],
        fontSize=12,
        textColor=primary,
        fontName="Helvetica-Bold",
        spaceBefore=10,
        spaceAfter=3,
        leading=16,
        keepWithNext=1,
    )
    synth_h3_style = ParagraphStyle(
        "SynthH3",
        parent=styles["Normal"],
        fontSize=10.5,
        textColor=secondary,
        fontName="Helvetica-Bold",
        spaceBefore=7,
        spaceAfter=2,
        leading=14,
        keepWithNext=1,
    )
    synth_heading_styles = [synth_h1_style, synth_h2_style, synth_h3_style]
    synth_bullet_style = ParagraphStyle(
        "SynthBullet",
        parent=synthesis_style,
        leftIndent=16,
        spaceAfter=3,
    )
    answer_bullet_style = ParagraphStyle(
        "AnswerBullet",
        parent=answer_style,
        leftIndent=16,
        spaceAfter=3,
    )
    # Answer sub-headings are a touch smaller than the synthesis ones.
    answer_heading_styles = [synth_h2_style, synth_h3_style, synth_h3_style]
    # Section summaries keep their italic body, but allow light headings.
    summary_heading_styles = [synth_h3_style, synth_h3_style, synth_h3_style]
    section_summary_bullet_style = ParagraphStyle(
        "SectionSummaryBullet",
        parent=section_summary_style,
        leftIndent=16,
        spaceAfter=3,
    )

    story: list[Any] = []

    # --- Summary lookups (by id) --------------------------------------
    synthesis_by_ddtype: dict[int | None, str] = {}  # dd_type_id -> synthesis text
    section_summary: dict[int | None, str] = {}  # section_id -> section summary text
    for s in summaries or []:
        if s.section_id is None:
            synthesis_by_ddtype[s.dd_type_id] = s.summary_text
        else:
            section_summary[s.section_id] = s.summary_text

    # --- Cover --------------------------------------------------------
    logo = _logo_size(banner, doc.width)
    if logo:
        story.append(Image(banner, width=logo[0], height=logo[1]))
    story.append(Spacer(1, 28))
    story.append(Paragraph(spaced_caps("Due Diligence Report"), label_style))
    story.append(
        HRFlowable(
            width="40%",
            thickness=1.2,
            color=primary,
            spaceBefore=6,
            spaceAfter=6,
            hAlign="CENTER",
        )
    )
    story.append(Paragraph(esc(company_name), cover_company_style))
    # NB: session.description holds the internal LLM prompt/instructions, so
    # it is intentionally NOT shown on this shareable cover page.
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            f"Report generated on {datetime.now().strftime('%d %B %Y')}",
            cover_meta_style,
        )
    )

    # --- Group answers: dd_type -> section -> [answers], keeping ids ---
    dd_order: list[int | None] = []  # DD types in the order they come
    dd_map: dict[int | None, dict[str, Any]] = {}  # dd_type_id -> name, sections
    for answer in answers:
        dt_obj = getattr(answer, "dd_type_obj", None)
        dt_id = dt_obj.id if dt_obj else None
        dt_name = dt_obj.name if dt_obj else "General"
        sec = getattr(answer, "section", None)
        sec_id = sec.id if sec else None
        sec_title = _section_title(answer)
        if dt_id not in dd_map:
            dd_map[dt_id] = {"name": dt_name, "sec_order": [], "sec_map": {}}
            dd_order.append(dt_id)
        entry = dd_map[dt_id]
        if sec_id not in entry["sec_map"]:
            entry["sec_map"][sec_id] = {"title": sec_title, "answers": []}
            entry["sec_order"].append(sec_id)
        entry["sec_map"][sec_id]["answers"].append(answer)

    # --- Body: per-DD-type synthesis (the readable report) ------------
    has_synthesis = any(dt_id in synthesis_by_ddtype for dt_id in dd_order)
    for dt_id in dd_order:
        text = synthesis_by_ddtype.get(dt_id)
        if not text:
            continue
        story.append(PageBreak())
        story.append(
            Paragraph(f"{esc('Synthesis')} &mdash; {esc(dd_map[dt_id]['name'])}", ddtype_style)
        )
        story.append(
            HRFlowable(width="100%", thickness=2, color=primary, spaceBefore=2, spaceAfter=14)
        )
        story.extend(
            markdown_to_flowables(
                text, synthesis_style, synth_heading_styles, synth_bullet_style, doc.width
            )
        )

    # --- Annex separator (only when a synthesis precedes it) ----------
    if has_synthesis:
        story.append(PageBreak())
        story.append(Paragraph(spaced_caps("Annexes"), annex_title_style))
        story.append(
            HRFlowable(
                width="40%",
                thickness=1.2,
                color=primary,
                spaceBefore=6,
                spaceAfter=6,
                hAlign="CENTER",
            )
        )

    # --- Detail (annex when synthesis present, else the whole body) ----
    for dt_id in dd_order:
        entry = dd_map[dt_id]
        story.append(PageBreak())
        story.append(Paragraph(f"{esc(entry['name'])} &mdash; {esc(company_name)}", ddtype_style))
        story.append(
            HRFlowable(width="100%", thickness=2, color=primary, spaceBefore=2, spaceAfter=14)
        )

        for sec_id in entry["sec_order"]:
            sec = entry["sec_map"][sec_id]
            section_name = sec["title"]
            section_answers = sec["answers"]
            # Section bar (navy background, white text)
            section_bar = Table(
                [[Paragraph(spaced_caps(section_name), section_style)]],
                colWidths=[doc.width],
            )
            section_bar.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), primary),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            section_header = [section_bar, Spacer(1, 8)]

            # Per-section summary (if generated) right under the section bar
            sec_summary = section_summary.get(sec_id)

            for idx, answer in enumerate(section_answers):
                # Question (no internal code shown — the report is shareable).
                # keepWithNext on the style keeps it attached to its answer.
                question_para = Paragraph(esc(_question_text(answer)), question_style)
                if idx == 0:
                    head = list(section_header)
                    if sec_summary:
                        head.extend(
                            markdown_to_flowables(
                                sec_summary,
                                section_summary_style,
                                summary_heading_styles,
                                section_summary_bullet_style,
                                doc.width,
                            )
                        )
                    # Keep the section bar (+ summary) with its first question so
                    # the header never strands alone at the bottom of a page.
                    story.append(KeepTogether(head + [question_para]))
                else:
                    story.append(question_para)
                answer_text = answer.answer_text or "No answer provided"
                story.extend(
                    markdown_to_flowables(
                        answer_text,
                        answer_style,
                        answer_heading_styles,
                        answer_bullet_style,
                        doc.width,
                    )
                )

                # Sources
                src_lines = format_sources(answer.sources)
                if src_lines:
                    story.append(Paragraph(spaced_caps("Sources"), source_label_style))
                    for line in src_lines:
                        story.append(Paragraph(line, source_style))

                story.append(
                    HRFlowable(
                        width="100%",
                        thickness=0.5,
                        color=rule,
                        spaceBefore=8,
                        spaceAfter=10,
                    )
                )

    # --- Page decoration (header band + confidential footer) ----------
    def _decorate(canvas, doc_):
        canvas.saveState()
        width, height = A4
        # Footer rule + notice + page number
        canvas.setStrokeColor(primary)
        canvas.setLineWidth(0.75)
        canvas.line(doc_.leftMargin, 34, width - doc_.rightMargin, 34)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(secondary)
        canvas.drawString(doc_.leftMargin, 25, settings.pdf_footer_notice)
        canvas.drawRightString(width - doc_.rightMargin, 25, f"Page {canvas.getPageNumber()}")
        # Running header (skip cover) - small banner top-right
        if canvas.getPageNumber() > 1:
            head = _logo_size(banner, 130)
            if head:
                canvas.drawImage(
                    banner,
                    width - doc_.rightMargin - head[0],
                    height - 42,
                    width=head[0],
                    height=head[1],
                    mask="auto",
                    preserveAspectRatio=True,
                )
            canvas.setStrokeColor(rule)
            canvas.setLineWidth(0.5)
            canvas.line(doc_.leftMargin, height - 46, width - doc_.rightMargin, height - 46)
        canvas.restoreState()

    doc.build(story, onFirstPage=_decorate, onLaterPages=_decorate)
    return buffer.getvalue()
