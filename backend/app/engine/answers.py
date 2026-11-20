"""A new answer row: the one place the copies of dd_answers are filled."""

from typing import Any

from app.models.answer import DDAnswer
from app.models.base import stored_id
from app.models.execution import DDExecution
from app.models.questions import DDQuestion


def new_answer(execution: DDExecution, question: DDQuestion, **fields: Any) -> DDAnswer:
    """The answer of `execution` to `question`, with `fields` (text, status...).

    Fills what follows from the two: the session and DD type of the run, the
    section of the question, and the codes as they read now, a copy at answer
    time (models/answer.py).
    """
    section = question.section
    if section is None:
        raise ValueError(f"Question {question.id} has no section")
    return DDAnswer(
        execution_id=stored_id(execution),
        question_id=stored_id(question),
        session_id=execution.session_id,
        dd_type_id=execution.dd_type_id,
        section_id=section.id,
        section_code=section.section_code,
        question_code=question.question_code,
        **fields,
    )
