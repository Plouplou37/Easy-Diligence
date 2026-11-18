"""
Data Export Utilities
Handle PDF and Excel report generation for various data types
"""
import html
import io
import json
import logging
import os
import re
from datetime import datetime

import pandas as pd
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
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

logger = logging.getLogger(__name__)


# --- Branding -------------------------------------------------------------
BRAND_NAVY = colors.HexColor("#243B5E")
BRAND_GREY = colors.HexColor("#4A4A4A")
BRAND_LIGHT = colors.HexColor("#E7EBF1")
CONFIDENTIAL_NOTICE = "PRIVATE AND CONFIDENTIAL — NOT FOR PUBLIC DISTRIBUTION"


def _banner_path():
    """Path of the optional PDF banner (BRAND_BANNER_PATH), or None.

    Unset means no banner. Set but missing (e.g. an optional volume that was
    not mounted) logs a warning and the report is produced without it.
    """
    path = settings.brand_banner_path
    if not path:
        return None
    if not os.path.isfile(path):
        logger.warning("BRAND_BANNER_PATH points to a missing file: %s", path)
        return None
    return path


def _esc(text) -> str:
    """Escape user/content text for reportlab Paragraph mini-markup."""
    return html.escape(str(text if text is not None else ""))


def _md_inline(text) -> str:
    """Convert inline markdown (**bold**, __bold__, links) to reportlab markup.

    No block handling (headings/line breaks): callers decide how to split
    blocks. Always returns escaped, paragraph-safe markup.
    """
    text = _esc(str(text if text is not None else ""))
    # Markdown links: [label](url) -> coloured hyperlink
    text = re.sub(
        r'\[([^\]]+)\]\((https?://[^)\s]+)\)',
        r'<a href="\2" color="#1F66B0">\1</a>',
        text,
    )
    # Bold: **text** and __text__ (non-greedy so edge/nested cases collapse)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    # Safety net: drop any orphan ** markers so raw markdown never shows.
    text = text.replace("**", "")
    return text


# A markdown table separator: |---|:---:|---:| and friends. Three dashes
# minimum, so a "- item" bullet can never be mistaken for one.
_TABLE_SEPARATOR = re.compile(r'^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$')

_ALIGNMENTS = {"LEFT": TA_LEFT, "CENTER": TA_CENTER, "RIGHT": TA_RIGHT}

# Bounds on how much of the width one column may claim. Raw text length as a
# weight would hand a 200-character column 97% of the page and squeeze a
# "Metric" column into nothing; clamping caps the ratio at roughly 10:1.
_COL_MIN_WEIGHT = 6
_COL_MAX_WEIGHT = 60

# Weights alone do not bound a column in points: with 11 columns, a short one
# came out at 8.7 pt, under its own 10 pt of padding, and reportlab aborted the
# whole export. Every column gets this floor first, the rest is shared by weight.
_COL_MIN_POINTS = 28
_CELL_PADDING = 5
_CELL_PADDING_TIGHT = 2
# Below this per-column width not even one character fits: the table is written
# out as plain text lines rather than failing the report.
_COL_MIN_DRAWABLE = 12


def _split_table_row(line: str) -> list:
    """The cells of one markdown table row, honouring escaped pipes."""
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [cell.strip().replace("\\|", "|") for cell in re.split(r'(?<!\\)\|', line)]


def _table_alignments(separator: str) -> list:
    """Per-column alignment, read from the colons in the separator row."""
    alignments = []
    for cell in _split_table_row(separator):
        left, right = cell.startswith(":"), cell.endswith(":")
        alignments.append("CENTER" if left and right else
                          "RIGHT" if right else "LEFT")
    return alignments


def _visible_length(text: str) -> int:
    """How wide a cell reads once rendered, not how long its markdown is.

    A cited source is usually ``[SEC](https://www.sec.gov/)``: 27
    characters of markdown for 3 on the page. Measuring the raw text would hand
    that column a third of the table.
    """
    text = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', r'\1', text or "")
    return len(text.replace("**", "").replace("__", ""))


def _table_col_widths(rows, available_width) -> list:
    """Share the width between columns, in proportion to what they hold."""
    columns = max(len(row) for row in rows)
    weights = []
    for index in range(columns):
        longest = max((_visible_length(row[index]) for row in rows
                       if index < len(row)), default=_COL_MIN_WEIGHT)
        weights.append(min(max(longest, _COL_MIN_WEIGHT), _COL_MAX_WEIGHT))
    if columns * _COL_MIN_POINTS >= available_width:
        return [available_width / columns] * columns
    spare = available_width - columns * _COL_MIN_POINTS
    total = sum(weights)
    return [_COL_MIN_POINTS + spare * weight / total for weight in weights]


def _markdown_table(rows, alignments, body_style, available_width):
    """A markdown table as a reportlab Table, styled like the rest of the report.

    Cells go through ``_md_inline``, so bold and links inside a table survive,
    and they are Paragraphs so a long cell wraps instead of running off the page.
    Returns None when the table has too many columns to draw at all.
    """
    columns = max(len(row) for row in rows)
    if available_width / columns < _COL_MIN_DRAWABLE:
        return None
    rows = [row + [""] * (columns - len(row)) for row in rows]   # ragged rows happen
    alignments = (alignments + ["LEFT"] * columns)[:columns]
    col_widths = _table_col_widths(rows, available_width)
    padding = (_CELL_PADDING if min(col_widths) >= _COL_MIN_POINTS
               else _CELL_PADDING_TIGHT)

    size = max(body_style.fontSize - 1, 7)
    base = {"parent": body_style, "fontSize": size, "leading": size + 2,
                "spaceBefore": 0, "spaceAfter": 0, "firstLineIndent": 0}
    styles = {}

    def cell(text, alignment, header):
        key = (alignment, header)
        if key not in styles:
            styles[key] = ParagraphStyle(
                f'MdCell{alignment}{"Head" if header else ""}',
                alignment=_ALIGNMENTS.get(alignment, TA_LEFT),
                textColor=BRAND_NAVY if header else body_style.textColor,
                fontName='Helvetica-Bold' if header else body_style.fontName,
                **base,
            )
        return Paragraph(_md_inline(text), styles[key])

    data = [[cell(text, alignments[i], row_index == 0)
             for i, text in enumerate(row)]
            for row_index, row in enumerate(rows)]

    # repeatRows so a table spanning a page break carries its header over.
    table = Table(data, colWidths=col_widths, hAlign='LEFT', repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor("#C7D0DC")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), padding),
        ('RIGHTPADDING', (0, 0), (-1, -1), padding),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return table


def _markdown_to_flowables(text, body_style, heading_styles, bullet_style,
                           available_width=None):
    """Split light markdown into a list of reportlab flowables with hierarchy.

    Recognises ATX headings (``#``..``######``), full-line bold pseudo-headings
    (``**Title**``), ``-``/``*`` bullets and ``1.`` numbered items, pipe tables,
    and blank lines as paragraph separators. ``heading_styles`` is a list indexed
    by heading depth (clamped to its length).

    ``available_width`` is the width a table may occupy (``doc.width`` at every
    call site). Tables are left as plain text without it, since a table with no
    column widths runs off the page.
    """
    from reportlab.platypus import Paragraph

    flowables = []
    if text is None:
        return flowables

    buf = []

    def flush():
        if buf:
            flowables.append(Paragraph("<br/>".join(buf), body_style))
            buf.clear()

    def heading(level, content):
        flush()
        style = heading_styles[min(level, len(heading_styles)) - 1]
        flowables.append(Paragraph(_md_inline(content), style))

    lines = str(text).split("\n")
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            flush()
            index += 1
            continue

        # A pipe table: a row of cells, then a |---|---| separator, then rows.
        # Both the row and the separator must carry a pipe, so a "---" rule on
        # its own is not mistaken for the start of one.
        following = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if (available_width and "|" in stripped
                and "|" in following and _TABLE_SEPARATOR.match(following)):
            rows = [_split_table_row(stripped)]
            end = index + 2
            while end < len(lines) and "|" in lines[end] and lines[end].strip():
                rows.append(_split_table_row(lines[end]))
                end += 1
            flush()
            table = _markdown_table(
                rows, _table_alignments(following), body_style, available_width)
            if table is None:
                # Too wide to draw: keep the content as one line per row.
                flowables.extend(Paragraph(_md_inline(" | ".join(row)), body_style)
                                 for row in rows)
            else:
                flowables.append(table)
            flowables.append(Spacer(1, 6))
            index = end
            continue

        index += 1
        m = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if m:
            heading(len(m.group(1)), m.group(2))
            continue
        # A line that is entirely bold reads as a sub-heading.
        mb = re.match(r'^\*\*(.+?)\*\*:?\s*$', stripped)
        if mb:
            heading(len(heading_styles), mb.group(1))
            continue
        ml = re.match(r'^[-*]\s+(.*)$', stripped)
        if ml:
            flush()
            flowables.append(Paragraph("•&nbsp;" + _md_inline(ml.group(1)), bullet_style))
            continue
        mn = re.match(r'^(\d+)\.\s+(.*)$', stripped)
        if mn:
            flush()
            flowables.append(Paragraph(f"{mn.group(1)}.&nbsp;" + _md_inline(mn.group(2)), bullet_style))
            continue
        buf.append(_md_inline(stripped))

    flush()
    return flowables


def _spaced_caps(text: str) -> str:
    """Render text as letter-spaced uppercase (institutional snapshot style).

    Uses non-breaking spaces so reportlab does not collapse the spacing, while
    preserving clear gaps between words. Each character is individually escaped
    so the result is safe to drop into a Paragraph.
    """
    words = (text or "").upper().split()
    spaced_words = [" ".join(_esc(ch) for ch in w) for w in words]
    return "   ".join(spaced_words)


# The reviewer's reference ("A.01"), as imports embed it in question codes
# ("A.01-_<digits>"), and as older question texts still open with it.
_CODE_REFERENCE = re.compile(r"^([A-Za-z]{1,3}\.?\d{1,3})-_")
_TEXT_REFERENCE = re.compile(r"^\s*[A-Za-z]{1,3}\.?\d{1,3}\s*-\s")


def _question_text(answer) -> str:
    """Question text lives on the related DDQuestion, not on DDAnswer.

    The reference ("A.01 - ") used to open the text itself; it now lives in the
    question code only. A report read by a committee still needs the numbering,
    so it is put back in front -- unless the text already opens with one, as it
    does for rows that predate the move.
    """
    question = getattr(answer, "question", None)
    if question is not None and getattr(question, "question_text", None):
        text = question.question_text
        match = _CODE_REFERENCE.match(answer.question_code or "")
        if match and not _TEXT_REFERENCE.match(text):
            return f"{match.group(1)} - {text}"
        return text
    return answer.question_code or "No question text"


def _section_title(answer) -> str:
    """Prefer the DDSection title, falling back to the legacy section_code."""
    section = getattr(answer, "section", None)
    if section is not None and getattr(section, "title", None):
        return section.title
    return answer.section_code or "General"


class AnswerExporter:
    """Export functionality for answer data"""

    @staticmethod
    def _logo_size(path, max_width):
        """Return (width, height) for the banner scaled to max_width, or None."""
        if not path:
            return None
        try:
            iw, ih = ImageReader(path).getSize()
            return max_width, max_width * ih / iw
        except Exception:
            logger.warning("Unreadable PDF banner, exported without it: %s", path)
            return None

    @staticmethod
    def generate_pdf_report(session, answers: list, summaries: list = None) -> Response:
        """Generate a branded PDF report for session answers.

        When ``summaries`` is provided, the report leads with a per-DD-type
        synthesis (the readable body) and pushes the question/answer/source
        detail into an annex (each section prefixed by its summary). When no
        summaries exist, it falls back to the original detail-only layout.
        """
        buffer = io.BytesIO()

        company_name = session.company.name if session.company else "N/A"

        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=50, leftMargin=50,   # ~0.7in sides
            topMargin=54, bottomMargin=44,   # leaves room for the running header/footer
            title=f"Due Diligence Report - {company_name}",
            author=settings.app_name,
        )
        banner = _banner_path()

        # --- Styles -------------------------------------------------------
        styles = getSampleStyleSheet()
        label_style = ParagraphStyle(
            'BrandLabel', parent=styles['Normal'],
            fontSize=12, textColor=BRAND_NAVY, alignment=TA_CENTER,
            spaceAfter=6, leading=18,
        )
        cover_company_style = ParagraphStyle(
            'CoverCompany', parent=styles['Heading1'],
            fontSize=26, textColor=BRAND_NAVY, alignment=TA_CENTER,
            spaceBefore=10, spaceAfter=6, leading=30,
        )
        cover_meta_style = ParagraphStyle(
            'CoverMeta', parent=styles['Normal'],
            fontSize=10, textColor=BRAND_GREY, alignment=TA_CENTER, leading=14,
        )
        ddtype_style = ParagraphStyle(
            'DDType', parent=styles['Heading1'],
            fontSize=17, textColor=BRAND_NAVY, spaceBefore=4, spaceAfter=6, leading=21,
        )
        section_style = ParagraphStyle(
            'SectionBar', parent=styles['Normal'],
            fontSize=11, textColor=colors.white, leading=15,
            fontName='Helvetica-Bold',
        )
        question_style = ParagraphStyle(
            'Question', parent=styles['Normal'],
            fontSize=11, textColor=BRAND_NAVY, fontName='Helvetica-Oblique',
            spaceBefore=2, spaceAfter=3, leading=15, keepWithNext=1,  # italic, never orphaned
        )
        answer_style = ParagraphStyle(
            'Answer', parent=styles['Normal'],
            fontSize=10, textColor=colors.HexColor("#1A1A1A"), alignment=TA_JUSTIFY,
            spaceAfter=4, leading=14,
        )
        source_label_style = ParagraphStyle(
            'SourceLabel', parent=styles['Normal'],
            fontSize=7, textColor=BRAND_NAVY, leading=11, spaceBefore=2, spaceAfter=1,
        )
        source_style = ParagraphStyle(
            'Source', parent=styles['Normal'],
            fontSize=8, textColor=BRAND_GREY, leading=11, leftIndent=10,
        )
        synthesis_style = ParagraphStyle(
            'Synthesis', parent=styles['Normal'],
            fontSize=10.5, textColor=colors.HexColor("#1A1A1A"), alignment=TA_JUSTIFY,
            spaceAfter=8, leading=16,
        )
        annex_title_style = ParagraphStyle(
            'AnnexTitle', parent=styles['Heading1'],
            fontSize=20, textColor=BRAND_NAVY, alignment=TA_CENTER,
            spaceBefore=10, spaceAfter=10, leading=24,
        )
        section_summary_style = ParagraphStyle(
            'SectionSummary', parent=styles['Normal'],
            fontSize=9.5, textColor=BRAND_GREY, alignment=TA_JUSTIFY,
            spaceBefore=4, spaceAfter=8, leading=14,
            fontName='Helvetica-Oblique',
        )

        # --- Heading / bullet styles for structured markdown content ------
        synth_h1_style = ParagraphStyle(
            'SynthH1', parent=styles['Heading2'],
            fontSize=14, textColor=BRAND_NAVY, fontName='Helvetica-Bold',
            spaceBefore=14, spaceAfter=5, leading=18, keepWithNext=1,
        )
        synth_h2_style = ParagraphStyle(
            'SynthH2', parent=styles['Heading3'],
            fontSize=12, textColor=BRAND_NAVY, fontName='Helvetica-Bold',
            spaceBefore=10, spaceAfter=3, leading=16, keepWithNext=1,
        )
        synth_h3_style = ParagraphStyle(
            'SynthH3', parent=styles['Normal'],
            fontSize=10.5, textColor=BRAND_GREY, fontName='Helvetica-Bold',
            spaceBefore=7, spaceAfter=2, leading=14, keepWithNext=1,
        )
        synth_heading_styles = [synth_h1_style, synth_h2_style, synth_h3_style]
        synth_bullet_style = ParagraphStyle(
            'SynthBullet', parent=synthesis_style,
            leftIndent=16, spaceAfter=3,
        )
        answer_bullet_style = ParagraphStyle(
            'AnswerBullet', parent=answer_style,
            leftIndent=16, spaceAfter=3,
        )
        # Answer sub-headings are a touch smaller than the synthesis ones.
        answer_heading_styles = [synth_h2_style, synth_h3_style, synth_h3_style]
        # Section summaries keep their italic body, but allow light headings.
        summary_heading_styles = [synth_h3_style, synth_h3_style, synth_h3_style]
        section_summary_bullet_style = ParagraphStyle(
            'SectionSummaryBullet', parent=section_summary_style,
            leftIndent=16, spaceAfter=3,
        )

        story = []

        # --- Summary lookups (by id) --------------------------------------
        synthesis_by_ddtype = {}   # dd_type_id -> synthesis text
        section_summary = {}       # section_id -> section summary text
        for s in (summaries or []):
            if s.section_id is None:
                synthesis_by_ddtype[s.dd_type_id] = s.summary_text
            else:
                section_summary[s.section_id] = s.summary_text

        # --- Cover --------------------------------------------------------
        logo = AnswerExporter._logo_size(banner, doc.width)
        if logo:
            story.append(Image(banner, width=logo[0], height=logo[1]))
        story.append(Spacer(1, 28))
        story.append(Paragraph(_spaced_caps("Due Diligence Report"), label_style))
        story.append(HRFlowable(width="40%", thickness=1.2, color=BRAND_NAVY,
                                spaceBefore=6, spaceAfter=6, hAlign='CENTER'))
        story.append(Paragraph(_esc(company_name), cover_company_style))
        # NB: session.description holds the internal LLM prompt/instructions, so
        # it is intentionally NOT shown on this shareable cover page.
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            f"Report generated on {datetime.now().strftime('%d %B %Y')}",
            cover_meta_style,
        ))

        # --- Group answers: dd_type -> section -> [answers], keeping ids ---
        dd_order = []   # preserve DD-type insertion order
        dd_map = {}     # dd_type_id -> {name, id, sec_order, sec_map}
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
            story.append(Paragraph(
                f"{_esc('Synthèse')} &mdash; {_esc(dd_map[dt_id]['name'])}", ddtype_style))
            story.append(HRFlowable(width="100%", thickness=2, color=BRAND_NAVY,
                                    spaceBefore=2, spaceAfter=14))
            story.extend(_markdown_to_flowables(
                text, synthesis_style, synth_heading_styles, synth_bullet_style,
                doc.width))

        # --- Annex separator (only when a synthesis precedes it) ----------
        if has_synthesis:
            story.append(PageBreak())
            story.append(Paragraph(_spaced_caps("Annexes"), annex_title_style))
            story.append(HRFlowable(width="40%", thickness=1.2, color=BRAND_NAVY,
                                    spaceBefore=6, spaceAfter=6, hAlign='CENTER'))

        # --- Detail (annex when synthesis present, else the whole body) ----
        for dt_id in dd_order:
            entry = dd_map[dt_id]
            story.append(PageBreak())
            story.append(Paragraph(f"{_esc(entry['name'])} &mdash; {_esc(company_name)}", ddtype_style))
            story.append(HRFlowable(width="100%", thickness=2, color=BRAND_NAVY,
                                    spaceBefore=2, spaceAfter=14))

            for sec_id in entry["sec_order"]:
                sec = entry["sec_map"][sec_id]
                section_name = sec["title"]
                section_answers = sec["answers"]
                # Section bar (navy background, white text)
                section_bar = Table(
                    [[Paragraph(_spaced_caps(section_name), section_style)]],
                    colWidths=[doc.width],
                )
                section_bar.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), BRAND_NAVY),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]))
                section_header = [section_bar, Spacer(1, 8)]

                # Per-section summary (if generated) right under the section bar
                sec_summary = section_summary.get(sec_id)

                for idx, answer in enumerate(section_answers):
                    # Question (no internal code shown — the report is shareable).
                    # keepWithNext on the style keeps it attached to its answer.
                    question_para = Paragraph(_esc(_question_text(answer)), question_style)
                    if idx == 0:
                        head = list(section_header)
                        if sec_summary:
                            head.extend(_markdown_to_flowables(
                                sec_summary, section_summary_style,
                                summary_heading_styles, section_summary_bullet_style,
                                doc.width))
                        # Keep the section bar (+ summary) with its first question so
                        # the header never strands alone at the bottom of a page.
                        story.append(KeepTogether(head + [question_para]))
                    else:
                        story.append(question_para)
                    answer_text = answer.answer_text or "No answer provided"
                    story.extend(_markdown_to_flowables(
                        answer_text, answer_style, answer_heading_styles,
                        answer_bullet_style, doc.width))

                    # Sources
                    src_lines = AnswerExporter._format_sources(answer.sources)
                    if src_lines:
                        story.append(Paragraph(_spaced_caps("Sources"), source_label_style))
                        for line in src_lines:
                            story.append(Paragraph(line, source_style))

                    story.append(HRFlowable(width="100%", thickness=0.5,
                                            color=BRAND_LIGHT, spaceBefore=8, spaceAfter=10))

        # --- Page decoration (header band + confidential footer) ----------
        def _decorate(canvas, doc_):
            canvas.saveState()
            width, height = A4
            # Footer rule + notice + page number
            canvas.setStrokeColor(BRAND_NAVY)
            canvas.setLineWidth(0.75)
            canvas.line(doc_.leftMargin, 34, width - doc_.rightMargin, 34)
            canvas.setFont('Helvetica', 7)
            canvas.setFillColor(BRAND_GREY)
            canvas.drawString(doc_.leftMargin, 25, CONFIDENTIAL_NOTICE)
            canvas.drawRightString(width - doc_.rightMargin, 25,
                                   f"Page {canvas.getPageNumber()}")
            # Running header (skip cover) - small banner top-right
            if canvas.getPageNumber() > 1:
                head = AnswerExporter._logo_size(banner, 130)
                if head:
                    canvas.drawImage(
                        banner, width - doc_.rightMargin - head[0],
                        height - 42, width=head[0], height=head[1],
                        mask='auto', preserveAspectRatio=True,
                    )
                canvas.setStrokeColor(BRAND_LIGHT)
                canvas.setLineWidth(0.5)
                canvas.line(doc_.leftMargin, height - 46,
                            width - doc_.rightMargin, height - 46)
            canvas.restoreState()

        doc.build(story, onFirstPage=_decorate, onLaterPages=_decorate)
        buffer.seek(0)

        safe_name = (session.name or f"session-{session.id}").replace(" ", "_")
        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={safe_name}_DD_Report.pdf"}
        )

    @staticmethod
    def _parse_sources(raw_sources) -> list[dict]:
        """Normalise the sources field into a flat list of source dicts.

        Mirrors the frontend parser (useSourceParser): sources may arrive as a
        JSON string, a dict grouped by files/web/webUrls/webSearchQueries, or a
        list of items (file_search with a `filenames` array, web/web_search,
        or plain strings).
        """
        if not raw_sources:
            return []
        parsed = raw_sources
        if isinstance(raw_sources, str):
            try:
                parsed = json.loads(raw_sources)
            except (json.JSONDecodeError, TypeError):
                return [{'type': 'file', 'filename': raw_sources}]

        items = []
        if isinstance(parsed, dict):
            for key, default_type in (
                ('files', 'file'), ('web', 'web'),
                ('webUrls', 'web'), ('webSearchQueries', 'web_search'),
            ):
                group = parsed.get(key)
                if isinstance(group, list):
                    for it in group:
                        if isinstance(it, dict):
                            items.append({**it, 'type': it.get('type', default_type)})
                        elif isinstance(it, str):
                            field = 'filename' if default_type == 'file' else 'url'
                            items.append({'type': default_type, field: it})
            if not items:
                items.append(parsed)  # a single source object
        elif isinstance(parsed, list):
            items = list(parsed)
        else:
            return []

        # Expand file_search entries (which carry several filenames) and
        # default the type for anything missing one.
        normalised = []
        for src in items:
            if isinstance(src, str):
                if src.startswith('http'):
                    normalised.append({'type': 'web', 'url': src})
                else:
                    normalised.append({'type': 'file', 'filename': src})
            elif isinstance(src, dict):
                if src.get('type') == 'file_search':
                    filenames = src.get('filenames') or (
                        [src['filename']] if src.get('filename') else [])
                    for fn in filenames:
                        normalised.append({'type': 'file_search', 'filename': fn})
                else:
                    normalised.append({
                        **src,
                        'type': src.get('type') or ('web' if src.get('url') else 'file'),
                    })
        return normalised

    @staticmethod
    def _format_sources(raw_sources) -> list[str]:
        """Build numbered, reportlab-ready source lines (links for web sources)."""
        lines, seen = [], set()
        for src in AnswerExporter._parse_sources(raw_sources):
            stype = src.get('type', '')
            if stype in ('web', 'web_search'):
                url = src.get('url') or src.get('content')
                if not url or url in seen:
                    continue
                seen.add(url)
                href = _esc(url)
                # Drop noisy tracking params from the visible text, keep full link
                display = url.split('?')[0] if 'utm_' in url else url
                lines.append(
                    f'Web &mdash; <a href="{href}" color="#1F66B0">{_esc(display)}</a>')
            elif stype in ('file', 'file_search'):
                name = src.get('filename') or src.get('content')
                if not name or ('file', name) in seen:
                    continue
                seen.add(('file', name))
                lines.append(f"Document &mdash; {_esc(name)}")
            else:
                value = src.get('url') or src.get('filename') or src.get('content')
                if not value or value in seen:
                    continue
                seen.add(value)
                lines.append(_esc(value))

        return [f"{i}. {line}" for i, line in enumerate(lines, 1)]

    @staticmethod
    def generate_excel_report(session, answers: list) -> Response:
        """Generate Excel report for session answers"""
        buffer = io.BytesIO()

        # Prepare data for Excel
        data = []
        for answer in answers:
            # Parse sources
            sources_text = ""
            if answer.sources:
                try:
                    sources = json.loads(answer.sources) if isinstance(answer.sources, str) else answer.sources
                    if sources:
                        sources_text = "; ".join([
                            f"{s.get('type', 'Unknown')}: {s.get('content', 'N/A')}"
                            for s in sources
                        ])
                except (json.JSONDecodeError, TypeError):
                    sources_text = str(answer.sources) if answer.sources else ""

            data.append({
                "DD Type": answer.dd_type_obj.name if answer.dd_type_obj else "N/A",
                "Section": _section_title(answer),
                "Question Code": answer.question_code or "N/A",
                "Question": _question_text(answer),
                "Answer": answer.answer_text or "No answer provided",
                "Sources": sources_text,
                # No confidence column: the score was a constant 0.8 written by
                # the engine, so it read as an assessment while measuring nothing.
                "Status": answer.status.value if answer.status else "N/A",
                "Manually Edited": "Yes" if answer.edited_by else "No",
                "Tokens Used": answer.tokens_used or 0,
                "Created At": answer.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        # Create DataFrame and Excel file
        df = pd.DataFrame(data)

        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Session summary sheet
            session_info = pd.DataFrame([
                ["Session ID", session.id],
                ["Asset Manager/Fund", session.company.name if session.company else "N/A"],
                ["Description", session.description or "N/A"],
                ["Created", session.created_at.strftime("%Y-%m-%d %H:%M:%S")],
                ["Total Answers", len(answers)]
            ], columns=["Property", "Value"])
            session_info.to_excel(writer, sheet_name='Session Info', index=False)

            # All answers sheet
            df.to_excel(writer, sheet_name='All Answers', index=False)

            # Separate sheets for each DD type (skip when there are no answers)
            if 'DD Type' in df.columns:
                for dd_type in df['DD Type'].unique():
                    dd_data = df[df['DD Type'] == dd_type]
                    sheet_name = dd_type.replace('_', ' ').title()[:31]  # Excel sheet name limit
                    dd_data.to_excel(writer, sheet_name=sheet_name, index=False)

        buffer.seek(0)

        return Response(
            content=buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={session.name}_DD_Report.xlsx"}
        )
