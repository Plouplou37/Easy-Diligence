"""Codes of sections and questions: A, B, ... and A.01, A.02, ...

A section is lettered by its position: A, B, ..., Z, then AA, AB... A question
is its section's letter and its rank: A.01. When an imported file gives the
reviewer's own reference ("A.01" in the provider's numbering), that reference
is the code. Codes are unique within a questionnaire; every questionnaire has
its own A.01.

Older codes carried a timestamp and a random suffix after the reference
("A.01-_96323997"): `reference_of` reads both shapes.
"""

import re
from collections import Counter
from collections.abc import Iterable
from typing import Any

# What a reference looks like, with the suffix of older codes.
_REFERENCE = re.compile(r"^([A-Za-z]{1,3}\.?\d{1,3})(?:-_\d*)?$")
_LETTERS = re.compile(r"^[A-Z]{1,3}$")
_RANKED = re.compile(r"^([A-Z]{1,3})\.(\d+)$")

MAX_CODE_LENGTH = 50  # the column's length


def section_letter(index: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA, 27 -> AB..."""
    letters = ""
    n = index + 1
    while n:
        n, rest = divmod(n - 1, 26)
        letters = chr(ord("A") + rest) + letters
    return letters


def _letter_index(letters: str) -> int:
    """The inverse of section_letter."""
    n = 0
    for char in letters:
        n = n * 26 + ord(char) - ord("A") + 1
    return n - 1


def question_code(section_code: str, rank: int) -> str:
    """The code of the rank-th question (from 1) of a section: A.01."""
    return f"{section_code}.{rank:02d}"


def reference_of(code: str | None) -> str | None:
    """The reference a code shows ("A.01"), or None for a code that has none."""
    match = _REFERENCE.match(code or "")
    return match.group(1).upper() if match else None


def _clean_reference(reference: Any) -> str | None:
    text = str(reference or "").strip().upper()
    return text[:MAX_CODE_LENGTH] or None


def assign_codes(sections: list[dict[str, Any]]) -> None:
    """Give codes to a parsed questionnaire, in place.

    Each section gets its letter. Each question gets its reference when the
    file gives one that no other question of the file repeats, and otherwise
    the next free A.01-style code of its section.
    """
    references = [
        _clean_reference(question.get("reference"))
        for section in sections
        for question in section["questions"]
    ]
    repeated = {ref for ref, count in Counter(references).items() if ref and count > 1}
    used = {ref for ref in references if ref and ref not in repeated}

    for index, section in enumerate(sections):
        letter = section_letter(index)
        section["section_code"] = letter
        rank = 0
        for question in section["questions"]:
            reference = _clean_reference(question.pop("reference", None))
            if reference and reference not in repeated:
                question["question_code"] = reference
                continue
            rank += 1
            while question_code(letter, rank) in used:
                rank += 1
            question["question_code"] = question_code(letter, rank)
            used.add(question["question_code"])


def next_section_code(existing: Iterable[str]) -> str:
    """The letter after the last one used in a questionnaire."""
    codes = set(existing)
    lettered = [_letter_index(code) for code in codes if _LETTERS.match(code)]
    index = max(lettered) + 1 if lettered else len(codes)
    while section_letter(index) in codes:
        index += 1
    return section_letter(index)


def next_question_code(section_code: str, existing: Iterable[str]) -> str:
    """The code after the last one used in a section: A.07 after A.06."""
    codes = set(existing)
    prefix = section_code if _LETTERS.match(section_code) else "Q"
    ranks = [
        int(match.group(2))
        for code in codes
        if (match := _RANKED.match(code)) and match.group(1) == prefix
    ]
    rank = max(ranks) + 1 if ranks else len(codes) + 1
    while question_code(prefix, rank) in codes:
        rank += 1
    return question_code(prefix, rank)
