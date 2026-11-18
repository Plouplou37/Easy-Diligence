"""Create a DD type from a questionnaire JSON, without going through HTTP.

Mirrors POST /dd-types/import (app/api/dd_types.py): same parser, same section
and question creation, same ownership semantics. Useful to load a questionnaire
without running the API and holding a JWT.

Usage:
    python backend/scripts/import_questionnaire.py <file.json> <CODE> <name> [owner_user_id]

The whole import runs in one transaction: nothing is written if any step fails.
"""
import sys

sys.path.insert(0, ".")

from app.database import SessionLocal                    # noqa: E402
from app.core.file_parser import DDTypeFileParser        # noqa: E402
from app.models.dd_types import DDType, DEFAULT_DD_TYPE_ICON   # noqa: E402
from app.models.questions import DDSection, DDQuestion   # noqa: E402


def import_questionnaire(path: str, code: str, name: str, owner_id):
    db = SessionLocal()
    try:
        if db.query(DDType).filter(DDType.code == code).first():
            raise SystemExit(f"Le code '{code}' existe deja")

        with open(path, "rb") as handle:
            sections_data = DDTypeFileParser().parse_file(handle.read(), path)

        dd_type = DDType(
            code=code,
            name=name,
            # No description rather than a filesystem path: the card shows this
            # to the analyst, and "Importe depuis ../example_questionnaire.json"
            # told them nothing about what the questionnaire covers.
            description=None,
            icon=DEFAULT_DD_TYPE_ICON,
            order_index=0,
            is_active=True,
            is_system=False,
            created_by=owner_id,
        )
        db.add(dd_type)
        db.flush()

        n_questions = 0
        for section_data in sections_data:
            section = DDSection(
                dd_type_id=dd_type.id,
                section_code=section_data["section_code"],
                title=section_data["title"],
                # No placeholder: "Section for <title>" restated the title on 213
                # of 217 rows. The description now reaches the model with the
                # section heading, so empty beats tautological.
                description=section_data.get("description"),
                order_index=section_data["order_index"],
            )
            db.add(section)
            db.flush()

            for question_data in section_data["questions"]:
                db.add(DDQuestion(
                    section_id=section.id,
                    question_code=question_data["question_code"],
                    question_text=question_data["question_text"],
                    context_prompt=question_data.get("context_prompt"),
                    order_index=question_data["order_index"],
                ))
                n_questions += 1

        db.commit()
        print(f"OK  id={dd_type.id}  code={dd_type.code}  "
              f"sections={len(sections_data)}  questions={n_questions}  "
              f"created_by={owner_id}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) not in (4, 5):
        raise SystemExit(__doc__)
    owner = int(sys.argv[4]) if len(sys.argv) == 5 else None
    import_questionnaire(sys.argv[1], sys.argv[2], sys.argv[3], owner)
