"""Codes of sections (A, B...) and questions (A.01...), and reading a questionnaire file."""

import io
import json
from pathlib import Path

import openpyxl
import pytest

from app.services.file_parser import DDTypeFileParser, FileParsingError
from app.services.question_codes import (
    assign_codes,
    next_question_code,
    next_section_code,
    reference_of,
    section_letter,
)


@pytest.mark.parametrize(
    ("index", "letters"), [(0, "A"), (1, "B"), (25, "Z"), (26, "AA"), (27, "AB"), (701, "ZZ")]
)
def test_section_letters(index, letters):
    assert section_letter(index) == letters


@pytest.mark.parametrize(
    ("code", "reference"),
    [
        ("A.01", "A.01"),
        ("ab.12", "AB.12"),
        ("A.01-_96323997", "A.01"),  # older codes: reference, then timestamp and random digits
        ("WHATIS_12345678", None),
        (None, None),
    ],
)
def test_reference_of(code, reference):
    assert reference_of(code) == reference


def _questionnaire(*sections):
    return [
        {"title": f"S{i}", "questions": [{"question_text": "?", "reference": r} for r in refs]}
        for i, refs in enumerate(sections)
    ]


def _codes(sections):
    return [[q["question_code"] for q in s["questions"]] for s in sections]


def test_codes_follow_the_position():
    sections = _questionnaire([None, None, None], [None])
    assign_codes(sections)
    assert [s["section_code"] for s in sections] == ["A", "B"]
    assert _codes(sections) == [["A.01", "A.02", "A.03"], ["B.01"]]


def test_a_reference_from_the_file_is_the_code():
    sections = _questionnaire([" a.01 ", "A.02"], ["B.07"])
    assign_codes(sections)
    assert _codes(sections) == [["A.01", "A.02"], ["B.07"]]
    assert "reference" not in sections[0]["questions"][0]


def test_codes_never_repeat():
    """A repeated reference falls back to the position, and a position never
    takes a code a reference already holds."""
    sections = _questionnaire(["A.02", None, "X.1", "X.1"])
    assign_codes(sections)
    codes = _codes(sections)[0]
    assert codes == ["A.02", "A.01", "A.03", "A.04"]
    assert len(set(codes)) == len(codes)


def test_next_codes():
    assert next_section_code([]) == "A"
    assert next_section_code(["A", "B"]) == "C"
    assert next_section_code(["A", "C"]) == "D"  # after the last, not in a gap
    assert next_section_code(["Z"]) == "AA"
    assert next_section_code(["LEGACY_123"]) == "B"  # one section already there

    assert next_question_code("A", []) == "A.01"
    assert next_question_code("A", ["A.01", "A.04"]) == "A.05"
    assert next_question_code("B", ["B.09"]) == "B.10"
    assert next_question_code("LEGACY_1", ["OLD_1"]) == "Q.02"


# --- Reading a file ------------------------------------------------------------------


def _xlsx(rows):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["Section", "Question"])
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_excel_file():
    content = _xlsx(
        [
            ["General", "Name of the fund?"],
            [None, "Date of launch?"],
            ["Team", "Size of the team?"],
        ]
    )
    sections = DDTypeFileParser().parse_file(content, "Questionnaire.XLSX")
    assert [(s["title"], s["section_code"]) for s in sections] == [("General", "A"), ("Team", "B")]
    assert _codes(sections) == [["A.01", "A.02"], ["B.01"]]
    assert sections[0]["questions"][1]["order_index"] == 1


def test_csv_file():
    content = b"Section,Question\nGeneral,Name of the fund?\n,Date of launch?\n"
    sections = DDTypeFileParser().parse_file(content, "questionnaire.csv")
    assert _codes(sections) == [["A.01", "A.02"]]


def test_json_file_keeps_the_references_and_sources():
    data = [
        {
            "section": "General",
            "description": "About the fund",
            "questions": [
                {"text": "Name?", "ref": "A.01", "context_prompt": "Prospectus, page 1"},
                "Date of launch?",
            ],
        },
        {"section": "Empty", "questions": []},
    ]
    sections = DDTypeFileParser().parse_file(json.dumps(data).encode(), "q.json")
    assert len(sections) == 1  # a section without questions is left out
    assert sections[0]["description"] == "About the fund"
    assert _codes(sections) == [["A.01", "A.02"]]
    assert sections[0]["questions"][0]["context_prompt"] == "Prospectus, page 1"


def test_the_example_questionnaire_imports():
    """The questionnaire the README tells newcomers to import."""
    example = Path(__file__).resolve().parents[2] / "examples" / "example_questionnaire.json"
    sections = DDTypeFileParser().parse_file(example.read_bytes(), example.name)
    assert [section["section_code"] for section in sections] == ["A", "B", "C", "D", "E", "F"]
    assert sum(len(codes) for codes in _codes(sections)) == 18
    assert all(section["description"] for section in sections)
    questions = [question for section in sections for question in section["questions"]]
    assert all(question["context_prompt"] for question in questions)


@pytest.mark.parametrize(
    ("content", "filename", "message"),
    [
        (b"not json", "q.json", "Invalid JSON"),
        (b'{"section": "x"}', "q.json", "array"),
        (b"Section,Question\n,Orphan question?\n", "q.csv", "without section"),
        (b"anything", "q.pdf", "Unsupported"),
    ],
)
def test_files_that_cannot_be_read(content, filename, message):
    with pytest.raises(FileParsingError, match=message):
        DDTypeFileParser().parse_file(content, filename)
