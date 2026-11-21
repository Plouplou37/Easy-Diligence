"""The request sent to OpenAI for one question, frozen.

The prompts and parameters were tuned and measured (docs/ARCHITECTURE.md, "The
answering engine"): a rework of the engine must not move them by accident.
The expected requests sit in tests/data/question_request.json, written once
from the engine as it was; a deliberate change rewrites that file, and the
diff shows exactly what goes to OpenAI differently.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.engine.openai_client as openai_client
from app.engine.openai_client import OpenAIProcessor
from app.engine.processor import DDProcessor

EXPECTED = Path(__file__).parent / "data" / "question_request.json"


class _Sent(Exception):
    """Stops the call once the request is captured."""


class _CapturingResponses:
    def __init__(self):
        self.requests = []

    def create(self, **request):
        self.requests.append(request)
        raise _Sent


def _question():
    """A question as the engine reads it: its section, its "where to look"."""
    section = SimpleNamespace(
        title="Investment strategy",
        description="How the fund invests, and within which limits.",
    )
    return SimpleNamespace(
        section=section,
        question_text="What is the fund's investment strategy?",
        context_prompt="Prospectus, section 3; latest factsheet.",
    )


@pytest.mark.parametrize("model", ["gpt-4o", "gpt-5"])
def test_the_request_for_a_question_does_not_move(monkeypatch, model):
    # Settings of their own, not those of a backend/.env on this machine.
    for name, value in {
        "openai_model": model,
        "reasoning_effort": "low",
        "tool_choice": "web_search",
        "compact_threshold": 200000,
    }.items():
        monkeypatch.setattr(openai_client.settings, name, value)

    processor = OpenAIProcessor()
    responses = _CapturingResponses()
    processor.client = SimpleNamespace(responses=responses)
    with pytest.raises(_Sent):
        processor.process_question(
            question_text=DDProcessor.compose_question_text(_question()),
            vector_store_ids=["vs_example"],
            previous_response_id="resp_previous",
            company_info={
                "name": "Example Asia Fund",
                "website_url": "https://example.com",
                "description": "A fictitious long-only Asian equity fund.",
                "management_company_name": "Example Fund Management",
                "management_company_website": None,
            },
        )

    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))[model]
    assert responses.requests[0] == expected
