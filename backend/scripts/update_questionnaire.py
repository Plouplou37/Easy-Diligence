"""Refresh the question texts of an existing DD type, in place.

The missing link between xlsx_to_questionnaire.py and the database. Importing
always creates a NEW dd type (POST /dd-types/import and import_questionnaire.py
both refuse an existing code), so a revised questionnaire had no way in: the
choice was a duplicate type or 205 calls to PUT /questions/questions/{id}.

What it writes is deliberately narrow -- question_text, nothing else:

* The codes stay. file_parser generates them from a timestamp plus a random
  suffix, so they cannot be reproduced; and dd_answers copies section_code /
  question_code at creation time and orders exports by them, so a new code
  would cut past answers loose from the structure they were written against.
* The ids stay, so existing answers keep pointing at their question.
* context_prompt is only ever filled in, never overwritten. Files can now carry
  it (it holds the "where to look" sources), but a value already in the database
  may have been typed by an analyst, and no file wins over that.
* The alignment check reads the reviewer's reference ("A.01") from the question
  code on the database side and from the 'ref' field on the file side, falling
  back to the head of the text for rows and files that still carry it there.
* The structure is checked, never reconciled. Sections and questions are
  matched by rank, and the script refuses to write unless the shapes agree.
  Adding or removing a question is a decision about existing answers, not a
  text refresh -- the script diagnoses the gap and stops.

Read-only by default. Nothing is written without --apply.

Usage:
    cd backend
    python scripts/update_questionnaire.py <file.json> <DD_TYPE_CODE> [--apply]

Exit code 1 on divergence, with nothing written. The update runs in one
transaction: nothing is written if any step fails.
"""
import json
import re
import sys

sys.path.insert(0, ".")

from sqlalchemy import or_  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models.answer import DDAnswer  # noqa: E402
from app.models.dd_types import DDType  # noqa: E402
from app.models.questions import DDQuestion, DDSection  # noqa: E402

# "A.01" -- the reviewer's own numbering on every reference question. Where both
# sides have it, it proves the alignment far better than the rank does: a
# question inserted and another dropped inside one section leaves the counts
# intact and would otherwise rewrite every following question with its
# neighbour's text.
#
# It used to open the question text ("A.01 - What is..."). It now lives in the
# question code on the database side and in a 'ref' field on the file side; the
# text pattern is kept for rows and files that still carry it there.
REFERENCE = re.compile(r"^\s*([A-Za-z]{1,3}\.?\d{1,3})\s*-\s")
CODE_REFERENCE = re.compile(r"^([A-Za-z]{1,3}\.?\d{1,3})-_")

MAX_SHOWN = 5


def reference_of(text: str):
    match = REFERENCE.match(text or "")
    return match.group(1).upper() if match else None


def db_reference_of(question):
    """A question's reference: from its code, or from its text for older rows."""
    match = CODE_REFERENCE.match(question.question_code or "")
    if match:
        return match.group(1).upper()
    return reference_of(question.question_text)


def file_reference_of(ref: str, text: str):
    """A file entry's reference: its 'ref' field, or its text for older files."""
    return (ref or "").strip().upper() or reference_of(text)


def load_sections(path: str) -> list:
    """The questionnaire as a list of (title, [(text, context_prompt, ref)]).

    Read raw on purpose: DDTypeFileParser would regenerate the codes.

    A question is either a bare string or an object carrying its own fields --
    the shape that lets a file hold the "where to look" sources outside the
    question text.
    """
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, list):
        raise SystemExit(f"{path}: la racine doit etre une liste de sections")

    def one(question):
        if isinstance(question, dict):
            text = question.get("text") or question.get("question_text") or ""
            return (str(text),
                    (question.get("context_prompt") or "").strip(),
                    (question.get("ref") or "").strip())
        return str(question), "", ""

    return [(str(entry["section"]).strip(),
             [one(question) for question in entry["questions"]])
            for entry in data]


def load_db_sections(db, dd_type_id: int) -> list:
    """Sections and their questions, in an order we chose.

    DDSection.questions has no order_by, so relying on it for a rank-based
    match would be trusting whatever order MySQL happens to return.
    """
    sections = (db.query(DDSection)
                .filter(DDSection.dd_type_id == dd_type_id)
                .order_by(DDSection.order_index, DDSection.id)
                .all())
    return [(section, db.query(DDQuestion)
             .filter(DDQuestion.section_id == section.id)
             .order_by(DDQuestion.order_index, DDQuestion.id)
             .all())
            for section in sections]


def check_structure(db_sections, file_sections) -> list:
    """Every reason not to write -- not just the first one."""
    problems = []

    if len(db_sections) != len(file_sections):
        problems.append(f"{len(db_sections)} sections en base contre "
                        f"{len(file_sections)} dans le fichier")

    for rank, ((section, questions), (title, texts)) in enumerate(
            zip(db_sections, file_sections, strict=False), 1):
        where = f"section {rank} '{section.title}'"

        if (section.title or "").strip() != title:
            problems.append(f"{where}: titre '{title}' dans le fichier")

        if len(questions) != len(texts):
            problems.append(f"{where}: {len(questions)} questions en base "
                            f"contre {len(texts)} dans le fichier")
            problems.extend(f"  {line}" for line in describe_gap(questions, texts))
            continue

        for rank_q, (question, (text, _, ref)) in enumerate(zip(questions, texts, strict=False), 1):
            old, new = db_reference_of(question), file_reference_of(ref, text)
            if old and new and old != new:
                problems.append(
                    f"{where}, question {rank_q} ({question.question_code}): "
                    f"reference {old} en base contre {new} dans le fichier "
                    f"-- alignement rompu"
                )

    return problems


def describe_gap(questions, texts) -> list:
    """Which references moved -- so a refusal is a report, not a dead end."""
    old = [db_reference_of(q) for q in questions]
    new = [file_reference_of(ref, text) for text, _, ref in texts]
    if None in old or None in new:
        return ["pas de numerotation exploitable pour situer l'ecart"]

    added = [r for r in new if r not in set(old)]
    removed = [r for r in old if r not in set(new)]
    lines = []
    if added:
        lines.append("ajoutees dans le fichier: " + ", ".join(added))
    if removed:
        lines.append("absentes du fichier: " + ", ".join(removed))
    return lines or ["memes references, effectifs differents: doublons ?"]


def describe_change(question, new_text: str) -> str:
    """The changed lines only -- these texts run to a dozen lines each."""
    old_lines = (question.question_text or "").splitlines()
    new_lines = new_text.splitlines()

    parts = [f"  {question.question_code} (id={question.id})"]
    parts += [f"    - {line}" for line in old_lines if line not in new_lines]
    parts += [f"    + {line}" for line in new_lines if line not in old_lines]
    return "\n".join(parts)


def count_answers(db, questions) -> int:
    """Answers pointing at these questions, by id or by code.

    question_id is nullable and older rows may carry only the code, so this can
    overcount. That is the direction to be wrong in.
    """
    if not questions:
        return 0
    return (db.query(DDAnswer)
            .filter(or_(DDAnswer.question_id.in_([q.id for q in questions]),
                        DDAnswer.question_code.in_([q.question_code
                                                    for q in questions])))
            .count())


def update_questionnaire(path: str, code: str, apply: bool, answered: bool) -> None:
    db = SessionLocal()
    try:
        dd_type = db.query(DDType).filter(DDType.code == code).first()
        if not dd_type:
            raise SystemExit(f"Le code '{code}' n'existe pas")

        db_sections = load_db_sections(db, dd_type.id)
        file_sections = load_sections(path)
        total = sum(len(texts) for _, texts in file_sections)

        print(f"DD type {dd_type.id} ({dd_type.code}): {len(db_sections)} sections, "
              f"{sum(len(q) for _, q in db_sections)} questions")
        print(f"Fichier {path}: {len(file_sections)} sections, {total} questions")

        problems = check_structure(db_sections, file_sections)
        if problems:
            print("\nLa structure diverge, rien n'a ete ecrit:")
            for problem in problems:
                print(f"  - {problem}")
            raise SystemExit("\nCorriger le fichier, ou traiter l'ajout / la "
                             "suppression de questions comme une operation a part.")

        # A question changes if its text moved, or if the file carries sources
        # for a question that has none. Sources already in the database are left
        # alone: they may have been edited by an analyst, and no file wins over
        # that.
        changed = []
        for (_, questions), (_, texts) in zip(db_sections, file_sections, strict=False):
            for question, (text, context, _ref) in zip(questions, texts, strict=False):
                text_moved = (question.question_text or "") != text
                fill_context = bool(context) and not (question.context_prompt or "").strip()
                if text_moved or fill_context:
                    changed.append((question, text, context if fill_context else None))

        if not changed:
            print(f"\nRien a faire: les {total} textes sont deja identiques.")
            return

        print()
        for question, text, context in changed[:MAX_SHOWN]:
            print(describe_change(question, text))
            if context:
                print(f"    + context_prompt: {context[:90]}"
                      f"{'...' if len(context) > 90 else ''}")
        if len(changed) > MAX_SHOWN:
            print(f"  ... et {len(changed) - MAX_SHOWN} autres")

        existing = count_answers(db, [question for question, _, _ in changed])
        if existing and not answered:
            raise SystemExit(
                f"\n{existing} reponse(s) referencent ces questions: les reecrire "
                "ferait passer d'anciennes reponses pour des reponses au nouveau "
                "texte. Relancer avec --answered si c'est voulu."
            )

        if not apply:
            print(f"\nDRY-RUN  {code}: {len(changed)}/{total} questions changeraient "
                  f"(relancer avec --apply pour ecrire)")
            return

        for question, text, context in changed:
            question.question_text = text
            if context:
                question.context_prompt = context

        db.commit()
        print(f"\nOK  {code}: {len(changed)}/{total} questions mises a jour "
              f"(ids, codes et order_index inchanges)")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    flags = {arg for arg in sys.argv[1:] if arg.startswith("--")}
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    if len(args) != 2 or flags - {"--apply", "--answered"}:
        raise SystemExit(__doc__)
    update_questionnaire(args[0], args[1],
                         apply="--apply" in flags,
                         answered="--answered" in flags)
