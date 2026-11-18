"""Document citations banned from answer text (core/openai_client.py).

gpt-5.6-luna loses text where OpenAI strips document-citation markers (see
CONSULTED_LABEL). The model is asked to name its documents on a last
"Documents consulted:" line instead; these tests cover rebuilding the document
sources from that line and asking again when markers slip through anyway.

A fake client stands in for OpenAI and nothing touches the database.
conftest.py imports the whole web app (and the .env it loads), so these run
on their own:
    python -m pytest tests/test_citation_format.py --noconftest -p no:cacheprovider
"""
from types import SimpleNamespace

from app.core.openai_client import (
    CONSULTED_LABEL,
    OpenAIProcessor,
    count_file_citations,
    documents_consulted,
)

PPM = {"file_id": "file-ppm", "filename": "1. PRIVATE PLACEMENT MEMORANDUM - Example Asia Fund Ltd.pdf"}
DECK = {"file_id": "file-deck", "filename": "EAF Presentation 202606.pdf"}
SUBS = {"file_id": "file-subs", "filename": "2a. SUBSCRIPTION DOCUMENTS FOR NON-U.S. INVESTORS.pdf"}
RESULTS = [PPM, DECK, PPM, SUBS]  # file_search returns several chunks per file


def _names(sources):
    return [s["filename"] for s in sources]


# --- documents_consulted -------------------------------------------------------

def test_names_matched_without_number_or_extension():
    answer = ("The PPM names the manager.\n\n"
              "**Documents consulted:** PRIVATE PLACEMENT MEMORANDUM - Example Asia Fund Ltd; "
              "EAF Presentation 202606.pdf")
    assert _names(documents_consulted(answer, RESULTS)) == [PPM["filename"], DECK["filename"]]


def test_bulleted_list_after_the_label():
    answer = "Answer.\n\nDocuments consulted:\n- 2a. SUBSCRIPTION DOCUMENTS FOR NON-U.S. INVESTORS.pdf\n"
    assert _names(documents_consulted(answer, RESULTS)) == [SUBS["filename"]]


def test_each_file_listed_once_with_its_id():
    answer = f"x\n{CONSULTED_LABEL} {PPM['filename']}; {PPM['filename']}"
    assert documents_consulted(answer, RESULTS) == [
        {"type": "file_search", "file_id": "file-ppm", "filename": PPM["filename"], "index": None}
    ]


def test_names_not_returned_by_the_search_are_ignored():
    answer = f"x\n{CONSULTED_LABEL} Annual Report 2025.pdf; none"
    assert documents_consulted(answer, RESULTS) == []


def test_no_line_means_no_document_source():
    assert documents_consulted("EAF Presentation 202606.pdf says so.", RESULTS) == []


def test_partial_word_is_not_a_match():
    short = {"file_id": "file-eaf", "filename": "EAF.pdf"}
    answer = f"x\n{CONSULTED_LABEL} EAFX Presentation.pdf"
    assert documents_consulted(answer, [short]) == []


# --- count_file_citations ------------------------------------------------------

def test_counts_only_file_citations_in_messages():
    response = {"output": [
        {"type": "file_search_call", "results": [PPM]},
        {"type": "message", "content": [{"annotations": [
            {"type": "file_citation", "index": 10},
            {"type": "url_citation", "start_index": 1, "end_index": 5},
            {"type": "file_citation", "index": 42},
        ]}]},
    ]}
    assert count_file_citations(response) == 2
    assert count_file_citations({"output": None}) == 0


# --- process_question ----------------------------------------------------------

class FakeResponses:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def create(self, **params):
        self.calls.append(params)
        return self.replies.pop(0)


def _reply(rid, text, annotations=(), results=(), tokens=100):
    output = []
    if results:
        output.append({"type": "file_search_call", "id": "fs_1", "results": list(results)})
    output.append({"type": "message", "id": f"msg_{rid}", "role": "assistant",
                   "content": [{"type": "output_text", "text": text, "annotations": list(annotations)}]})
    dump = {"id": rid, "status": "completed", "model": "gpt-5.6-luna",
            "output": output, "usage": {"total_tokens": tokens}}
    return SimpleNamespace(
        id=rid, status="completed", model="gpt-5.6-luna", output_text=text, output=output,
        usage=SimpleNamespace(total_tokens=tokens, input_tokens=tokens - 10, output_tokens=10),
        error=None, incomplete_details=None, model_dump=lambda: dump,
    )


def _processor(replies):
    # Built by hand so no API key is needed: same fields as __init__.
    processor = OpenAIProcessor.__new__(OpenAIProcessor)
    processor.model = "gpt-5.6-luna"
    processor.is_reasoning_model = True
    processor.web_search_tool = "web_search"
    processor.client = SimpleNamespace(responses=FakeResponses(replies))
    return processor


CLEAN = f"The manager is Example Fund Management.\n\n{CONSULTED_LABEL} EAF Presentation 202606.pdf"


def test_clean_answer_keeps_one_call_and_rebuilds_document_sources():
    processor = _processor([_reply("resp_1", CLEAN, results=[PPM, DECK])])
    result = processor.process_question("Q?", ["vs_1"])
    assert len(processor.client.responses.calls) == 1
    assert result["answer"] == CLEAN
    assert _names(result["sources"]["files"]) == [DECK["filename"]]
    assert result["sources"]["total_count"] == 1
    assert result["tokens_used"] == 100


def test_markers_despite_the_rule_ask_again_once_and_count_both_calls():
    holed = _reply("resp_1", "Place of regis: Luxembourg",
                   annotations=[{"type": "file_citation", "index": 14,
                                 "file_id": "file-ppm", "filename": PPM["filename"]}],
                   results=[PPM], tokens=120)
    processor = _processor([holed, _reply("resp_2", CLEAN, results=[DECK], tokens=100)])
    result = processor.process_question("Q?", ["vs_1"])
    assert len(processor.client.responses.calls) == 2
    assert result["response_id"] == "resp_2"
    assert result["answer"] == CLEAN
    assert result["tokens_used"] == 220


def test_markers_twice_keep_the_second_answer_and_its_citations():
    citation = {"type": "file_citation", "index": 3, "file_id": "file-ppm", "filename": PPM["filename"]}
    processor = _processor([
        _reply("resp_1", "abc", annotations=[citation], results=[PPM]),
        _reply("resp_2", "def", annotations=[citation], results=[PPM]),
    ])
    result = processor.process_question("Q?", ["vs_1"])
    assert len(processor.client.responses.calls) == 2
    assert result["answer"] == "def"
    assert _names(result["sources"]["files"]) == [PPM["filename"]]


# --- prompt --------------------------------------------------------------------

def test_rule_only_when_documents_are_attached():
    processor = _processor([])
    with_docs = processor._build_system_prompt({"name": "Example Asia Fund"}, has_documents=True)
    without = processor._build_system_prompt({"name": "Example Asia Fund"}, has_documents=False)
    assert "citation markers must NOT appear" in with_docs
    assert CONSULTED_LABEL in with_docs
    assert CONSULTED_LABEL not in without
