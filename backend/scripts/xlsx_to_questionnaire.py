"""Convert a consolidated questionnaire workbook (.xlsx) into import JSON.

The reviewed questionnaires carry more columns than the importer understands:
the parser only accepts ``[{"section": str, "questions": [str, ...]}]`` and
stores each question as plain text. The guidance columns (expected answer
format, documents to look at, analytical purpose) are therefore folded INTO the
question text -- which is exactly what reaches the model, so the guidance is
actually used rather than merely stored.

Column names differ between questionnaires (one workbook has "Expected answer
format" / "Applicable to" / "Document / evidence expected", another has
"Applicability" / "Analytical purpose" / "Expected answer / evidence"), so
columns are mapped by header name, never by position.

Usage:
    python backend/scripts/xlsx_to_questionnaire.py <input.xlsx> <output.json>
"""

import json
import re
import sys

import openpyxl

# Normalised header -> label used in the generated question text.
# Order matters: it is the order the hints appear under each question.
# Which entity a theme is about. A DD covers both the fund and the company
# running it, and answering about the wrong one is a common failure of the web
# search -- so every question states its level explicitly.
#
# Matching is a case-insensitive substring test on the theme, first hit wins;
# anything unmatched defaults to the fund. Kept as a plain table so a reviewer
# can check and correct it without reading the code.
MANAGEMENT_COMPANY_THEMES = [
    "management company",
    "investment manager",
    "investment advisor",
    "research company",
    "key people",
    "investment team",
    "governance of the investment team",
    "key persons",
    # Firm-level risk function: its purposes are about independence, seniority
    # and empowerment of the risk team, not about the fund's own risk figures.
    "risk management - team",
]

LEVEL_FUND = "Fund"
LEVEL_MANAGEMENT_COMPANY = "Management Company"

HINT_COLUMNS = [
    ("sub-theme", "Topic"),
    ("expected answer format", "Expected answer format"),
    ("applicable to", "Applies to"),
    ("applicability", "Applies to"),
    ("analytical purpose", "Analytical purpose"),
]

# The columns naming the documents to consult. They go to their own field
# (context_prompt) rather than into the question text: this is the one
# instruction an analyst wants to adjust per company, and it must be editable.
# Workbooks name that column differently -- "Document / evidence expected" in
# one, "Expected answer / evidence" in another -- which is how questionnaires
# end up saying the same thing under two labels. Mapping both here is what
# makes them speak the same language downstream.
SOURCE_COLUMNS = [
    "document / evidence expected",
    "expected answer / evidence",
]


def norm(value) -> str:
    """Normalise a header cell for comparison."""
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def clean(value) -> str:
    """Flatten a cell value to a single line of readable text."""
    text = re.sub(r"\s*\n\s*", " ", str(value or "")).strip()
    return re.sub(r"\s{2,}", " ", text).strip(" -")


def clean_hint(value) -> str:
    """Flatten a guidance cell, turning its bullet list into an enumeration.

    The evidence columns are bullet lists ("- Prospectus and/or\\n- Factsheets
    ..."); naive flattening would read "Prospectus and/or - Factsheets". Strip
    the bullets and the trailing "and/or", then join with semicolons.
    """
    items = []
    for line in str(value or "").splitlines():
        item = re.sub(r"^[-•*]\s*", "", line).strip()
        item = re.sub(r"\s*and/or\s*$", "", item, flags=re.IGNORECASE).strip()
        item = re.sub(r"\s{2,}", " ", item)
        if item:
            items.append(item)
    return "; ".join(items)


def find_header_row(worksheet, limit: int = 15):
    """Locate the header row (the one holding a 'question' column)."""
    for row in range(1, min(limit, worksheet.max_row) + 1):
        headers = {
            norm(worksheet.cell(row=row, column=col).value): col
            for col in range(1, worksheet.max_column + 1)
            if worksheet.cell(row=row, column=col).value
        }
        if "question" in headers:
            return row, headers
    raise SystemExit("No header row containing a 'Question' column was found")


def level_for_theme(theme: str) -> str:
    """Whether a theme is about the fund or about its management company."""
    haystack = (theme or "").lower()
    for needle in MANAGEMENT_COMPANY_THEMES:
        if needle in haystack:
            return LEVEL_MANAGEMENT_COMPANY
    return LEVEL_FUND


def build_reference(worksheet, row: int, headers: dict) -> str:
    """The reviewer's numbering ("A.01"), emitted apart from the text.

    It used to open the question text ("A.01 - What is..."), where it ended up
    shown twice on screen, next to the question code built from it. It now
    travels in its own 'ref' field, from which the importer builds the code.
    """
    if "no." not in headers:
        return ""
    return clean(worksheet.cell(row=row, column=headers["no."]).value)


def build_question_text(worksheet, row: int, headers: dict, theme: str = "") -> str:
    """Question text plus the reviewer's guidance, as one string.

    Neither the reference nor the sources are in it: build_reference and
    build_sources emit them into their own fields.
    """
    question = clean(worksheet.cell(row=row, column=headers["question"]).value)

    lines = [question, ""]
    lines.append(f"Level: {level_for_theme(theme)}")

    seen = set()
    for header, label in HINT_COLUMNS:
        col = headers.get(header)
        if col is None or label in seen:
            continue
        value = clean_hint(worksheet.cell(row=row, column=col).value)
        if value:
            lines.append(f"{label}: {value}")
            seen.add(label)

    return "\n".join(lines).strip()


def build_sources(worksheet, row: int, headers: dict) -> str:
    """The documents to consult, from whichever column this workbook uses."""
    for header in SOURCE_COLUMNS:
        col = headers.get(header)
        if col is None:
            continue
        value = clean_hint(worksheet.cell(row=row, column=col).value)
        if value:
            return value
    return ""


def convert(xlsx_path: str) -> list:
    worksheet = openpyxl.load_workbook(xlsx_path, data_only=True).active
    header_row, headers = find_header_row(worksheet)

    theme_col = headers.get("theme")
    if theme_col is None:
        raise SystemExit("No 'Theme' column found: cannot build sections")

    sections = []
    by_title = {}

    for row in range(header_row + 1, worksheet.max_row + 1):
        question = clean(worksheet.cell(row=row, column=headers["question"]).value)
        if not question:
            continue  # section banner or spacer row
        theme = clean(worksheet.cell(row=row, column=theme_col).value)
        if not theme:
            continue

        section = by_title.get(theme)
        if section is None:
            section = {"section": theme, "questions": []}
            by_title[theme] = section
            sections.append(section)

        text = build_question_text(worksheet, row, headers, theme)
        sources = build_sources(worksheet, row, headers)
        reference = build_reference(worksheet, row, headers)
        # A bare string when there is nothing else to carry, so questionnaires
        # without numbering or a sources column keep the original, simpler shape.
        if reference or sources:
            entry = {}
            if reference:
                entry["ref"] = reference
            entry["text"] = text
            if sources:
                entry["context_prompt"] = sources
            section["questions"].append(entry)
        else:
            section["questions"].append(text)

    return sections


def main(argv):
    if len(argv) != 3:
        raise SystemExit(__doc__)

    sections = convert(argv[1])
    with open(argv[2], "w", encoding="utf-8") as handle:
        json.dump(sections, handle, ensure_ascii=False, indent=2)

    total = sum(len(s["questions"]) for s in sections)
    print(f"{argv[2]}: {len(sections)} sections, {total} questions")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
