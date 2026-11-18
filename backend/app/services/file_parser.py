"""Reading a questionnaire file (Excel, CSV or JSON) into sections and questions.

The readers give the structure; `parse_file` then gives the codes
(services/question_codes.py): A, B... for the sections, A.01... for the
questions, or the reviewer's reference when a JSON file carries one.
"""

import json
from io import BytesIO
from typing import Any

import openpyxl
import pandas as pd

from app.services.question_codes import assign_codes

Section = dict[str, Any]


class FileParsingError(Exception):
    """The file cannot be read as a questionnaire. The message says why, for the user."""


def _new_section(title: Any, order: int, description: str | None = None) -> Section:
    return {
        "title": str(title).strip(),
        "description": description,
        "order_index": order,
        "questions": [],
    }


def _rows_to_sections(rows: list[tuple[int, Any, Any]], kind: str) -> list[Section]:
    """Sections from (row number, section cell, question cell) rows: a section
    cell opens a new section, a question cell adds a question to it."""
    sections: list[Section] = []
    current: Section | None = None
    for row_number, section_name, question_text in rows:
        if not section_name and not question_text:
            continue
        if section_name:
            current = _new_section(section_name, len(sections))
            sections.append(current)
        if question_text:
            if current is None:
                raise FileParsingError(f"Question found without section at row {row_number}")
            current["questions"].append(
                {
                    "question_text": str(question_text).strip(),
                    "order_index": len(current["questions"]),
                }
            )
    if not sections:
        raise FileParsingError(f"No valid sections found in {kind} file")
    return sections


class DDTypeFileParser:
    """Reads a questionnaire file: one section per block, one question per row."""

    def parse_excel(self, file_content: bytes) -> list[Section]:
        """Column A: the section (on its first row only); column B: the question.
        The first row is a header."""
        try:
            worksheet = openpyxl.load_workbook(BytesIO(file_content)).active
        except Exception as error:
            raise FileParsingError(f"Error parsing Excel file: {error}") from error
        if worksheet is None:
            raise FileParsingError("The Excel file has no sheet")

        rows = []
        for row_number, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), 2):
            section_name = row[0] if len(row) > 0 and row[0] else None
            question_text = row[1] if len(row) > 1 and row[1] else None
            rows.append((row_number, section_name, question_text))
        return _rows_to_sections(rows, "Excel")

    def parse_csv(self, file_content: bytes) -> list[Section]:
        """Column 1: the section (on its first row only); column 2: the question.
        The first row is a header."""
        for encoding in ("utf-8", "utf-8-sig", "latin1", "cp1252"):
            try:
                text = file_content.decode(encoding)
                frame = pd.read_csv(BytesIO(text.encode("utf-8")))
                break
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
            except Exception as error:
                raise FileParsingError(f"Error parsing CSV file: {error}") from error
        else:
            raise FileParsingError("Unable to parse CSV file with any supported encoding")

        if frame.empty or len(frame.columns) < 2:
            raise FileParsingError("CSV must have at least 2 columns (Section, Question)")

        def cell(value: Any) -> Any:
            return value if pd.notna(value) and str(value).strip() else None

        rows = [
            (position + 2, cell(row.iloc[0]), cell(row.iloc[1]))
            for position, (_, row) in enumerate(frame.iterrows())
        ]
        return _rows_to_sections(rows, "CSV")

    def parse_json(self, file_content: bytes) -> list[Section]:
        """A list of sections:

            [{"section": "Name", "description": "...", "questions": [...]}]

        A question is a string, or an object with "text", and optionally
        "context_prompt" (where to look) and "ref" (the reviewer's reference,
        kept as the question's code).
        """
        try:
            data = json.loads(file_content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise FileParsingError(f"Invalid JSON format: {error}") from error
        if not isinstance(data, list):
            raise FileParsingError("JSON must be an array of section objects")

        sections: list[Section] = []
        for position, section_data in enumerate(data, 1):
            if not isinstance(section_data, dict):
                raise FileParsingError(f"Section {position} must be an object")
            name = section_data.get("section")
            questions = section_data.get("questions", [])
            if not name:
                raise FileParsingError(f"Section {position} missing 'section' field")
            if not isinstance(questions, list):
                raise FileParsingError(f"Questions for section '{name}' must be an array")

            section = _new_section(name, len(sections), section_data.get("description"))
            for entry in questions:
                if isinstance(entry, dict):
                    text = entry.get("text") or entry.get("question_text")
                    context_prompt = (entry.get("context_prompt") or "").strip() or None
                    reference = (entry.get("ref") or "").strip() or None
                else:
                    text, context_prompt, reference = entry, None, None
                if not text or not str(text).strip():
                    continue
                section["questions"].append(
                    {
                        "question_text": str(text).strip(),
                        "order_index": len(section["questions"]),
                        "context_prompt": context_prompt,
                        "reference": reference,
                    }
                )
            if section["questions"]:  # a section without questions is left out
                sections.append(section)

        if not sections:
            raise FileParsingError("No valid sections with questions found in JSON file")
        return sections

    def parse_file(self, file_content: bytes, filename: str) -> list[Section]:
        """The questionnaire in the file, with its codes:

        [{"title", "section_code", "description", "order_index",
          "questions": [{"question_text", "question_code", "order_index",
                         "context_prompt"?}]}]
        """
        name = filename.lower()
        if name.endswith((".xlsx", ".xls")):
            sections = self.parse_excel(file_content)
        elif name.endswith(".csv"):
            sections = self.parse_csv(file_content)
        elif name.endswith(".json"):
            sections = self.parse_json(file_content)
        else:
            raise FileParsingError(
                "Unsupported file format. Supported formats: .xlsx, .xls, .csv, .json"
            )
        assign_codes(sections)
        return sections
