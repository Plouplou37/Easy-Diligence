"""Markdown, as the model writes it, turned into reportlab flowables.

Inline bold and links, headings, bullets and tables. Every text goes through
`esc` first: reportlab paragraphs read a small HTML-like markup.
"""

import html
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from app.core.config import settings


def esc(text) -> str:
    """Escape user/content text for reportlab Paragraph mini-markup."""
    return html.escape(str(text if text is not None else ""))


def _md_inline(text) -> str:
    """Convert inline markdown (**bold**, __bold__, links) to reportlab markup.

    No block handling (headings/line breaks): callers decide how to split
    blocks. Always returns escaped, paragraph-safe markup.
    """
    text = esc(str(text if text is not None else ""))
    # Markdown links: [label](url) -> coloured hyperlink
    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        r'<a href="\2" color="#1F66B0">\1</a>',
        text,
    )
    # Bold: **text** and __text__ (non-greedy so edge/nested cases collapse)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    # Safety net: drop any orphan ** markers so raw markdown never shows.
    text = text.replace("**", "")
    return text


# A markdown table separator: |---|:---:|---:| and friends. Three dashes
# minimum, so a "- item" bullet can never be mistaken for one.
_TABLE_SEPARATOR = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$")

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
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", line)]


def _table_alignments(separator: str) -> list:
    """Per-column alignment, read from the colons in the separator row."""
    alignments = []
    for cell in _split_table_row(separator):
        left, right = cell.startswith(":"), cell.endswith(":")
        alignments.append("CENTER" if left and right else "RIGHT" if right else "LEFT")
    return alignments


def _visible_length(text: str) -> int:
    """How wide a cell reads once rendered, not how long its markdown is.

    A cited source is usually ``[SEC](https://www.sec.gov/)``: 27
    characters of markdown for 3 on the page. Measuring the raw text would hand
    that column a third of the table.
    """
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"\1", text or "")
    return len(text.replace("**", "").replace("__", ""))


def _table_col_widths(rows, available_width) -> list:
    """Share the width between columns, in proportion to what they hold."""
    columns = max(len(row) for row in rows)
    weights = []
    for index in range(columns):
        longest = max(
            (_visible_length(row[index]) for row in rows if index < len(row)),
            default=_COL_MIN_WEIGHT,
        )
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
    rows = [row + [""] * (columns - len(row)) for row in rows]  # ragged rows happen
    alignments = (alignments + ["LEFT"] * columns)[:columns]
    col_widths = _table_col_widths(rows, available_width)
    padding = _CELL_PADDING if min(col_widths) >= _COL_MIN_POINTS else _CELL_PADDING_TIGHT

    size = max(body_style.fontSize - 1, 7)
    base = {
        "parent": body_style,
        "fontSize": size,
        "leading": size + 2,
        "spaceBefore": 0,
        "spaceAfter": 0,
        "firstLineIndent": 0,
    }
    styles = {}

    def cell(text, alignment, header):
        key = (alignment, header)
        if key not in styles:
            styles[key] = ParagraphStyle(
                f"MdCell{alignment}{'Head' if header else ''}",
                alignment=_ALIGNMENTS.get(alignment, TA_LEFT),
                textColor=colors.HexColor(settings.pdf_primary_color)
                if header
                else body_style.textColor,
                fontName="Helvetica-Bold" if header else body_style.fontName,
                **base,
            )
        return Paragraph(_md_inline(text), styles[key])

    data = [
        [cell(text, alignments[i], row_index == 0) for i, text in enumerate(row)]
        for row_index, row in enumerate(rows)
    ]

    # repeatRows so a table spanning a page break carries its header over.
    table = Table(data, colWidths=col_widths, hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(settings.pdf_rule_color)),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C7D0DC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), padding),
                ("RIGHTPADDING", (0, 0), (-1, -1), padding),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def markdown_to_flowables(text, body_style, heading_styles, bullet_style, available_width=None):
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
        if (
            available_width
            and "|" in stripped
            and "|" in following
            and _TABLE_SEPARATOR.match(following)
        ):
            rows = [_split_table_row(stripped)]
            end = index + 2
            while end < len(lines) and "|" in lines[end] and lines[end].strip():
                rows.append(_split_table_row(lines[end]))
                end += 1
            flush()
            table = _markdown_table(rows, _table_alignments(following), body_style, available_width)
            if table is None:
                # Too wide to draw: keep the content as one line per row.
                flowables.extend(Paragraph(_md_inline(" | ".join(row)), body_style) for row in rows)
            else:
                flowables.append(table)
            flowables.append(Spacer(1, 6))
            index = end
            continue

        index += 1
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            heading(len(m.group(1)), m.group(2))
            continue
        # A line that is entirely bold reads as a sub-heading.
        mb = re.match(r"^\*\*(.+?)\*\*:?\s*$", stripped)
        if mb:
            heading(len(heading_styles), mb.group(1))
            continue
        ml = re.match(r"^[-*]\s+(.*)$", stripped)
        if ml:
            flush()
            flowables.append(Paragraph("•&nbsp;" + _md_inline(ml.group(1)), bullet_style))
            continue
        mn = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if mn:
            flush()
            flowables.append(
                Paragraph(f"{mn.group(1)}.&nbsp;" + _md_inline(mn.group(2)), bullet_style)
            )
            continue
        buf.append(_md_inline(stripped))

    flush()
    return flowables


def spaced_caps(text: str) -> str:
    """Render text as letter-spaced uppercase (institutional snapshot style).

    Uses non-breaking spaces so reportlab does not collapse the spacing, while
    preserving clear gaps between words. Each character is individually escaped
    so the result is safe to drop into a Paragraph.
    """
    words = (text or "").upper().split()
    spaced_words = [" ".join(esc(ch) for ch in w) for w in words]
    return "   ".join(spaced_words)
