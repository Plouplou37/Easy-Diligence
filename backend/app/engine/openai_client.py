import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.engine.errors import ResponseError

logger = logging.getLogger(__name__)

# Model families that reason internally (GPT-5.x, GPT-6, o-series). Two API
# differences matter here:
#   - they REJECT sampling parameters: sending 'temperature' at all returns a
#     400, whatever its value;
#   - they expect the modern hosted-tool name 'web_search'; 'web_search_preview'
#     is the legacy name, still accepted by gpt-4o.
# Keeping both paths lets us fall back to gpt-4o by changing OPENAI_MODEL alone.
REASONING_MODEL_PREFIXES = ("gpt-5", "gpt-6", "o1", "o3", "o4")

# Hidden reasoning tokens are billed as output AND consume max_output_tokens:
# too small a budget returns status='incomplete' with no visible answer, billed
# all the same. OpenAI advises reserving ~25k.
#
# The effort itself is a setting rather than a constant because the two uses of
# the model do not want the same one: answering a question is extraction from
# documents already retrieved (settings.reasoning_effort, "low" -- measured good:
# 72 questions in 14 min, no failure), while a summary is pure drafting from
# answers already written, which is exactly where more reasoning pays
# (settings.summary_reasoning_effort).
REASONING_MIN_OUTPUT_TOKENS = 25000

# Citation markers the model sometimes leaves in its text without attaching the
# matching annotation. They showed up verbatim on the review screen and in the
# PDF. Three shapes, all OpenAI's own:
#   "【】"                  an empty placeholder;
#   "【4:0†source.pdf】"     the older file citation, recognisable by its "†";
#   a newer token such as "turn7file6", opened either by "【" or by U+E200 plus a
#   label ("filecite") plus U+E202, possibly chaining several tokens separated by
#   U+E202, and always closed by U+E201.
# Anything else between 【】 is left alone: an Asian fund's documents may well
# quote a title that way. Leading spaces go with the marker, never newlines.
#
# The private-use delimiters are spelled with chr() on purpose. Written as raw
# characters they are invisible in an editor, and the pattern then reads as if
# it swallowed whole lines -- which it does not: every part of it is bounded.
_CITE_OPEN, _CITE_SEP, _CITE_CLOSE = chr(0xE200), chr(0xE202), chr(0xE201)
_CITE_TOKEN = r"turn\d+[a-z]+\d+"
_CITATION_MARKER = re.compile(
    r"[ \t]*(?:"
    + r"【】"
    + r"|【[^】\n]*†[^】\n]*】"
    + r"|【?"
    + r"(?:"
    + _CITE_OPEN
    + r"[^"
    + _CITE_SEP
    + _CITE_CLOSE
    + r"\n]*"
    + _CITE_SEP
    + r")?"
    + r"(?:"
    + _CITE_TOKEN
    + _CITE_SEP
    + r")*"
    + _CITE_TOKEN
    + _CITE_CLOSE
    + r")"
)


def strip_citation_markers(text: str) -> str:
    """Remove orphan OpenAI citation markers from an answer's text."""
    if not text:
        return text
    return _CITATION_MARKER.sub("", text)


# Document citations cost text under gpt-5.6-luna. Measured 07/10/2026: 101 of
# the 144 luna answers had words cut in half ("Place of regis:",
# "websitetps://"), every hole sitting exactly at a file_citation index and
# the shift growing citation after citation. It happens on OpenAI's side, when
# it strips the model's document-citation markers: its own stored copy
# (responses.retrieve) carries the same holes, and the streamed deltas are
# already cut. gpt-4o answers do not show it.
#
# So the model is told not to emit those markers at all (_build_system_prompt)
# and to name the documents it used on a last "Documents consulted:" line,
# from which the document sources are rebuilt (documents_consulted). It still
# slips now and then (1 run in 8 when measured): process_question then asks
# again once.
CONSULTED_LABEL = "Documents consulted:"
_LEADING_NUMBER = re.compile(r"^\s*\w{1,3}[.)]\s+")  # "1. ", "2a. ", "10) "


def _normalise_name(text: str) -> str:
    """Lowercase words separated by single spaces, punctuation dropped."""
    return " ".join(re.findall(r"[a-z0-9]+", (text or "").lower()))


def count_file_citations(response_dict: dict[str, Any]) -> int:
    """Number of document-citation annotations in a response's messages."""
    count = 0
    for item in response_dict.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            for annotation in (part or {}).get("annotations") or []:
                if isinstance(annotation, dict) and annotation.get("type") == "file_citation":
                    count += 1
    return count


def documents_consulted(
    answer_text: str, search_results: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Document sources named on the answer's "Documents consulted:" line.

    Only files the search actually returned can be listed, so a name the model
    made up never becomes a source. The comparison ignores case, punctuation,
    the extension and a leading number ("1. PRIVATE PLACEMENT MEMORANDUM...")
    that the model tends to drop. Everything after the label counts, whether
    the names follow on the same line or as a bulleted list.
    """
    if not answer_text or not search_results:
        return []
    key = CONSULTED_LABEL.rstrip(":").lower()
    position = answer_text.lower().rfind(key)
    if position < 0:
        return []
    named = f" {_normalise_name(answer_text[position + len(key) :])} "

    sources, seen = [], set()
    for result in search_results:
        if not isinstance(result, dict):
            continue
        file_id, filename = result.get("file_id"), result.get("filename")
        if not filename or file_id in seen:
            continue
        stem = os.path.splitext(filename)[0]
        candidates = {_normalise_name(stem), _normalise_name(_LEADING_NUMBER.sub("", stem))}
        if any(candidate and f" {candidate} " in named for candidate in candidates):
            seen.add(file_id)
            sources.append(
                {
                    "type": "file_search",
                    "file_id": file_id,
                    "filename": filename,
                    "index": None,
                }
            )
    return sources


def is_reasoning_model(model: str) -> bool:
    """Whether the model belongs to a family that rejects sampling params."""
    return (model or "").lower().startswith(REASONING_MODEL_PREFIXES)


class OpenAIProcessor:
    def __init__(self):
        # No retry in the SDK: the engine has the only retry policy
        # (engine/errors.py), so that retry_count counts the real calls and a
        # question never goes past MAX_ATTEMPTS calls.
        self.client = OpenAI(api_key=settings.openai_api_key.get_secret_value(), max_retries=0)
        self.model = settings.openai_model
        self.is_reasoning_model = is_reasoning_model(self.model)
        self.web_search_tool = "web_search" if self.is_reasoning_model else "web_search_preview"
        logger.info(
            "OpenAI model: %s (reasoning=%s, web tool=%s)",
            self.model,
            self.is_reasoning_model,
            self.web_search_tool,
        )

    def _apply_model_params(
        self,
        request_params: dict[str, Any],
        temperature: float,
        max_output_tokens: int,
        reasoning_effort: str | None = None,
    ) -> None:
        """Apply the sampling / output-budget parameters the model accepts.

        Classic models (gpt-4o) take 'temperature' and the caller's token
        budget as-is. Reasoning models reject sampling parameters entirely and
        need headroom for their hidden reasoning tokens.

        'reasoning_effort' defaults to the question-answering setting; callers
        doing something else (summaries) pass their own.
        """
        if self.is_reasoning_model:
            request_params["max_output_tokens"] = max(
                max_output_tokens, REASONING_MIN_OUTPUT_TOKENS
            )
            request_params["reasoning"] = {"effort": reasoning_effort or settings.reasoning_effort}
        else:
            request_params["temperature"] = temperature
            request_params["max_output_tokens"] = max_output_tokens

    def _apply_compaction(self, request_params: dict[str, Any]) -> None:
        """Ask the server to compact the conversation chain past a threshold.

        Questions are chained with previous_response_id, which grows the input by
        ~4 200 tokens each time: a long DD would exceed the context window and
        truncation='auto' would then drop the earliest answers without telling
        anyone. Compaction replaces that history with a compressed item instead.

        Sent through 'extra_body' because the pinned SDK (2.2.0) predates the
        parameter and would reject it client-side; the API itself validates it
        (an unknown type or field comes back as a 400).
        """
        if not self.is_reasoning_model or settings.compact_threshold <= 0:
            return
        request_params["extra_body"] = {
            "context_management": [
                {"type": "compaction", "compact_threshold": settings.compact_threshold}
            ]
        }

    def create_vector_store(self, name: str, expires_after_days: int | None = None) -> str:
        """Create a vector store for document analysis with optional expiration policy"""
        try:
            params: dict[str, Any] = {"name": name}

            # Add expiration policy if specified
            if expires_after_days:
                params["expires_after"] = {"anchor": "last_active_at", "days": expires_after_days}

            vector_store = self.client.vector_stores.create(**params)
            return vector_store.id
        except Exception as e:
            logger.error("Error creating vector store: %s", e)
            raise

    def upload_file(self, file_content: bytes, filename: str) -> str:
        """Upload a file to OpenAI for analysis"""
        try:
            file_tuple = (filename, BytesIO(file_content))
            file_obj = self.client.files.create(file=file_tuple, purpose="assistants")
            logger.info("Uploaded file %s with ID %s", filename, file_obj.id)
            return file_obj.id
        except Exception as e:
            logger.error("Error uploading file %s: %s", filename, e)
            raise

    def add_file_to_vector_store(
        self, vector_store_id: str, file_id: str, chunking_strategy: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Add a file to an existing vector store with optional chunking strategy"""
        try:
            params: dict[str, Any] = {"vector_store_id": vector_store_id, "file_id": file_id}

            if chunking_strategy:
                params["chunking_strategy"] = chunking_strategy
                logger.info("Adding file %s to vector store with custom chunking strategy", file_id)
            else:
                logger.debug("Adding file %s to vector store with auto chunking", file_id)

            self.client.vector_stores.files.create(**params)
            return {"status": "success", "file_id": file_id, "vector_store_id": vector_store_id}
        except Exception as e:
            logger.error("Error adding file to vector store: %s", e)
            raise

    def wait_for_file_indexed(
        self, vector_store_id: str, file_id: str, timeout: int = 30, interval: int = 2
    ) -> bool:
        """Best-effort wait until a vector store file is indexed (status 'completed').

        Used right after attaching a file so a subsequent file_search can see it.
        Never raises: returns True if indexed, False on timeout/failure/error.
        """
        elapsed = 0
        while elapsed < timeout:
            try:
                f = self.client.vector_stores.files.retrieve(
                    file_id=file_id, vector_store_id=vector_store_id
                )
                status = getattr(f, "status", None)
                if status == "completed":
                    return True
                if status == "failed":
                    logger.warning("File %s failed to index in %s", file_id, vector_store_id)
                    return False
            except Exception as e:
                logger.warning("Error polling file %s status: %s", file_id, e)
                return False
            time.sleep(interval)
            elapsed += interval
        logger.warning("File %s not indexed within %ss (continuing anyway)", file_id, timeout)
        return False

    def build_question_request(
        self,
        question_text: str,
        vector_store_ids: list[str],
        previous_response_id: str | None = None,
        company_info: dict[str, Any] | None = None,
        tool_choice: str | dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """The responses.create() parameters for one DD question.

        Kept apart from process_question so a measurement script can send the
        engine's exact request instead of a copy that would drift from it.
        """
        # Build the system prompt
        # The research rule differs with and without documents: telling the
        # model to search a collection that is not there would invite it to
        # imply one was reviewed.
        system_prompt = self._build_system_prompt(
            company_info, has_documents=bool(vector_store_ids)
        )

        # Prepare the request parameters for responses.create()
        # Using proper message array structure with roles
        request_params = {
            "model": self.model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": question_text}]},
            ],
            "store": True,  # Enable prompt caching for cost savings
            "truncation": "auto",  # Automatically drop old messages when context is full
            "include": [
                "file_search_call.results",
                "web_search_call.action.sources",
            ],  # Include search results and web sources
        }
        self._apply_model_params(request_params, temperature=0.1, max_output_tokens=4000)
        self._apply_compaction(request_params)

        # Add tools based on what's available
        # Using plain dictionary format as expected by responses.create() API
        tools = []

        # Add file search tool if vector stores are available
        if vector_store_ids:
            tools.append(
                {
                    "type": "file_search",
                    "vector_store_ids": vector_store_ids,
                    "max_num_results": 20,
                    "ranking_options": {"ranker": "auto", "score_threshold": 0.2},
                }
            )

        # Always add web search
        tools.append(
            {
                "type": self.web_search_tool,
                "user_location": {"type": "approximate"},
                "search_context_size": "medium",
            }
        )
        logger.debug("Added %s tools to request", len(tools))

        if tools:
            request_params["tools"] = tools

        # tool_choice: an explicit argument wins; otherwise the setting
        # decides. Its default is "web_search": config.py records the
        # measurement that kept it ("auto" lost the web corroboration for
        # next to no saving).
        #
        # The dispatch is written out value by value on purpose: the previous
        # 'elif tool_choice:' let falsy values ("" or {}) fall through and
        # send nothing at all, which looked like a decision but wasn't one.
        # An unknown value falls back to the default, never to "auto".
        if tool_choice is not None:
            request_params["tool_choice"] = tool_choice
            logger.debug("Using caller-supplied tool_choice: %s", tool_choice)
        else:
            choice = (settings.tool_choice or "web_search").strip().lower()
            if choice not in ("auto", "web_search", "none"):
                logger.warning(
                    "Unknown TOOL_CHOICE setting %r; falling back to 'web_search'",
                    settings.tool_choice,
                )
                choice = "web_search"
            if choice == "web_search":
                request_params["tool_choice"] = {"type": self.web_search_tool}
            elif choice == "auto":
                request_params["tool_choice"] = "auto"
            # "none": send no tool_choice, leaving the API to its own default
            logger.debug("Using configured tool_choice: %s", choice)

        # Add previous_response_id for context chaining if available
        if previous_response_id:
            request_params["previous_response_id"] = previous_response_id
            logger.debug("Added previous_response_id for context chaining")

        logger.debug(
            "Request params: model=%s, input_messages=%s, tools=%s",
            request_params["model"],
            len(request_params["input"]),
            len(tools),
        )
        return request_params

    @staticmethod
    def _cites_documents_with_markers(response) -> bool:
        """Whether a completed response carries document-citation annotations."""
        if response is None or getattr(response, "status", None) != "completed":
            return False
        if not hasattr(response, "model_dump"):
            return False
        return count_file_citations(response.model_dump()) > 0

    def process_question(
        self,
        question_text: str,
        vector_store_ids: list[str],
        previous_response_id: str | None = None,
        company_info: dict[str, Any] | None = None,
        tool_choice: str | dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Process a single question using OpenAI's responses.create() with previous_response_id chaining
        This maintains the exact API structure requested by the user
        """
        try:
            logger.debug("Processing question with OpenAI API")

            request_params = self.build_question_request(
                question_text, vector_store_ids, previous_response_id, company_info, tool_choice
            )

            # Make the API call using client.responses.create()
            response = self.client.responses.create(**request_params)

            # The prompt forbids document-citation markers because OpenAI cuts
            # text where it strips them (see CONSULTED_LABEL). When the model
            # uses them anyway, the answer probably has holes: ask once more.
            # The discarded call is billed all the same, so its tokens count.
            discarded_tokens = 0
            if self._cites_documents_with_markers(response):
                logger.warning(
                    "Response %s cites documents with markers despite the prompt: its text may have holes, asking again once",
                    response.id,
                )
                discarded_tokens = response.usage.total_tokens if response.usage else 0
                response = self.client.responses.create(**request_params)
                if self._cites_documents_with_markers(response):
                    logger.warning(
                        "Response %s cites documents with markers again: kept, its text may have holes",
                        response.id,
                    )

            # Comprehensive response validation
            if response is None:
                raise ResponseError("OpenAI API returned None response")

            logger.info("OpenAI API response received successfully")

            # An incomplete response (failed, cut short) is no answer: it is
            # raised as a ResponseError, which the engine retries.
            response_status = getattr(response, "status", "unknown")
            logger.info("Response status: %s", response_status)

            if response_status != "completed":
                error_details = ""

                # Extract structured error information if available
                if hasattr(response, "error") and response.error:
                    error_type = getattr(response.error, "type", "unknown")
                    error_message = getattr(response.error, "message", "No error message")
                    error_details = f" Error: {error_type} - {error_message}"
                    logger.error("OpenAI API Error: %s - %s", error_type, error_message)

                # Extract incomplete details if available
                if hasattr(response, "incomplete_details") and response.incomplete_details:
                    incomplete_reason = getattr(response.incomplete_details, "reason", "unknown")
                    error_details += f" Incomplete: {incomplete_reason}"
                    logger.warning("Response incomplete: %s", incomplete_reason)

                raise ResponseError(
                    f"OpenAI response not completed. Status: {response_status}.{error_details}"
                )

            # Verify correct model was used
            response_model = getattr(response, "model", "unknown")
            logger.info("Response generated by model: %s", response_model)

            if response_model != self.model:
                logger.warning("Model mismatch! Requested: %s, Got: %s", self.model, response_model)
            logger.debug("Response ID: %s", getattr(response, "id", "unknown"))
            logger.debug("Response type: %s", type(response))
            logger.debug("Has output_text: %s", hasattr(response, "output_text"))
            logger.debug("Has output: %s", hasattr(response, "output"))

            if hasattr(response, "output_text"):
                logger.debug(
                    "output_text length: %s",
                    len(response.output_text) if response.output_text else 0,
                )
            if hasattr(response, "output") and response.output:
                logger.debug("output items count: %s", len(response.output))

            # Log token usage if available (including cache info)
            if hasattr(response, "usage") and response.usage:
                usage = response.usage

                # Extract basic token counts
                total_tokens = getattr(usage, "total_tokens", 0)
                input_tokens = getattr(usage, "input_tokens", 0)
                output_tokens = getattr(usage, "output_tokens", 0)

                # Log full usage object for debugging
                logger.debug("Full usage object: %s", usage)

                # Check for cached tokens in various possible locations
                cached_tokens = 0
                cache_creation_tokens = 0
                cache_read_tokens = 0

                # Try input_tokens_details (standard location)
                if hasattr(usage, "input_tokens_details"):
                    details = usage.input_tokens_details
                    logger.debug("input_tokens_details: %s", details)

                    if hasattr(details, "cached_tokens"):
                        cached_tokens = details.cached_tokens
                    elif isinstance(details, dict) and "cached_tokens" in details:
                        cached_tokens = details["cached_tokens"]

                    # Check for cache_creation_input_tokens
                    if hasattr(details, "cache_creation_input_tokens"):
                        cache_creation_tokens = details.cache_creation_input_tokens
                    elif isinstance(details, dict) and "cache_creation_input_tokens" in details:
                        cache_creation_tokens = details["cache_creation_input_tokens"]

                    # Check for cache_read_input_tokens
                    if hasattr(details, "cache_read_input_tokens"):
                        cache_read_tokens = details.cache_read_input_tokens
                    elif isinstance(details, dict) and "cache_read_input_tokens" in details:
                        cache_read_tokens = details["cache_read_input_tokens"]

                # Build comprehensive log message
                log_msg = f"TOKEN USAGE - Total: {total_tokens} | Input: {input_tokens} | Output: {output_tokens}"

                if cached_tokens > 0 or cache_creation_tokens > 0 or cache_read_tokens > 0:
                    log_msg += " | CACHE - "
                    cache_parts = []
                    if cache_read_tokens > 0:
                        cache_parts.append(f"Read: {cache_read_tokens}")
                    if cache_creation_tokens > 0:
                        cache_parts.append(f"Created: {cache_creation_tokens}")
                    if cached_tokens > 0:
                        cache_parts.append(f"Cached: {cached_tokens}")
                    log_msg += ", ".join(cache_parts)
                    logger.warning(log_msg)  # Use WARNING to make cache hits very visible
                else:
                    logger.info(log_msg)

            # Extract answer and metadata from responses.create() output
            answer_text = ""
            sources = []

            # Get response as dictionary for accessing output array
            response_dict = response.model_dump() if hasattr(response, "model_dump") else {}

            # Debug logging for response structure (only when needed)
            logger.debug("Response dict keys: %s", list(response_dict.keys()))
            if "output" in response_dict and response_dict["output"]:
                logger.debug("Output array length: %s", len(response_dict["output"]))

            # Use simple method first - direct text access
            if hasattr(response, "output_text") and response.output_text:
                answer_text = response.output_text
                logger.debug("Extracted answer using output_text: %s chars", len(answer_text))

            # Extract sources from detailed output structure
            try:
                logger.debug("Starting source extraction")
                # First collect all file citations for fallback use
                file_citations = {}  # file_id -> filename mapping

                # Extract vector store IDs from tools for fallback file retrieval
                vector_store_ids_from_response = []
                if "tools" in response_dict and response_dict["tools"]:
                    for tool in response_dict["tools"]:
                        if isinstance(tool, dict) and tool.get("type") == "file_search":
                            vs_ids = tool.get("vector_store_ids", [])
                            if vs_ids:
                                vector_store_ids_from_response.extend(vs_ids)
                                logger.debug("Found vector store IDs in response: %s", vs_ids)

                if "output" in response_dict and response_dict["output"] is not None:
                    # Ensure response.output is iterable (list)
                    output_list = (
                        response_dict["output"]
                        if isinstance(response_dict["output"], (list, tuple))
                        else []
                    )
                    logger.debug(
                        "Processing %s output items for source extraction", len(output_list)
                    )

                    # First pass: collect all file citations
                    for output_item in output_list:
                        if isinstance(output_item, dict) and output_item.get("type") == "message":
                            content = output_item.get("content", [])
                            if isinstance(content, list):
                                for content_item in content:
                                    if (
                                        isinstance(content_item, dict)
                                        and content_item.get("type") == "text"
                                    ):
                                        text_data = content_item.get("text", {})
                                        annotations = (
                                            text_data.get("annotations", [])
                                            if isinstance(text_data, dict)
                                            else []
                                        )
                                        for annotation in annotations:
                                            if (
                                                isinstance(annotation, dict)
                                                and annotation.get("type") == "file_citation"
                                            ):
                                                file_id = annotation.get("file_id")
                                                filename = annotation.get("filename")
                                                if file_id and filename:
                                                    file_citations[file_id] = filename
                                                    logger.debug(
                                                        "Collected file citation: %s -> %s",
                                                        file_id,
                                                        filename,
                                                    )

                    logger.debug("Collected %s file citations for fallback", len(file_citations))

                    for i, output_item in enumerate(output_list):
                        if output_item is None:
                            logger.debug("Output item %s: NULL item, skipping", i)
                            continue

                        # Handle dict format responses (main path)
                        if isinstance(output_item, dict):
                            item_type = output_item.get("type", None)
                            logger.debug("Processing output item %s: type='%s'", i, item_type)

                            # Log tool calls for debugging but don't create sources from them
                            if item_type == "file_search_call":
                                logger.info(
                                    "Found file search tool call: %s", output_item.get("id")
                                )
                                # Don't create source - actual citations come from message annotations

                            elif item_type == "web_search_call":
                                action = output_item.get("action", {})
                                logger.info("Found web search tool call: %s", action.get("query"))
                                # Don't create source - actual citations come from message annotations

                            # Handle message output - extract sources from annotations
                            elif item_type == "message":
                                content = output_item.get("content", [])
                                if content and isinstance(content, (list, tuple)):
                                    logger.debug(
                                        "Processing message with %s content items", len(content)
                                    )

                                    for _j, content_item in enumerate(content):
                                        if (
                                            not isinstance(content_item, dict)
                                            or "annotations" not in content_item
                                        ):
                                            continue

                                        annotations_list = content_item["annotations"]
                                        if not annotations_list:
                                            continue

                                        logger.info("Found %s citations", len(annotations_list))

                                        for annotation in annotations_list:
                                            if not isinstance(annotation, dict):
                                                continue

                                            ann_type = annotation.get("type", "")

                                            # Web search citations
                                            if ann_type == "url_citation":
                                                url = annotation.get("url", "")
                                                title = annotation.get("title", "")
                                                logger.info("Found web citation: %s", url)
                                                sources.append(
                                                    {
                                                        "type": "web_search",
                                                        "url": url,
                                                        "title": title,
                                                        "start_index": annotation.get(
                                                            "start_index"
                                                        ),
                                                        "end_index": annotation.get("end_index"),
                                                    }
                                                )

                                            # File search citations
                                            elif ann_type == "file_citation":
                                                file_id = annotation.get("file_id", "")
                                                filename = annotation.get("filename", "")
                                                index = annotation.get("index", 0)
                                                logger.info("Found file citation: %s", filename)
                                                sources.append(
                                                    {
                                                        "type": "file_search",
                                                        "file_id": file_id,
                                                        "filename": filename,
                                                        "index": index,
                                                    }
                                                )

                logger.info("Source extraction complete: Found %s sources", len(sources))

            except Exception as e:
                logger.error("Error extracting sources from response output: %s", e)
                # Continue without sources - we still have the answer text

            # Extract actual messages from OpenAI response output and build answer_text
            messages = []

            # Add user message (we don't have an ID for this as it's our input)
            messages.append(
                {
                    "role": "user",
                    "content": question_text,
                    "id": None,  # User input doesn't have OpenAI message ID
                }
            )

            # Extract assistant messages with actual OpenAI IDs from response.output
            if "output" in response_dict and response_dict["output"] is not None:
                output_list = (
                    response_dict["output"]
                    if isinstance(response_dict["output"], (list, tuple))
                    else []
                )

                for output_item in output_list:
                    if output_item is None:
                        continue

                    # Look for message objects with IDs (handle both dict and object formats)
                    item_type = (
                        getattr(output_item, "type", None)
                        if hasattr(output_item, "type")
                        else output_item.get("type")
                        if isinstance(output_item, dict)
                        else None
                    )

                    if item_type == "message":
                        # Handle both object and dict formats
                        if isinstance(output_item, dict):
                            message_id = output_item.get("id")
                            role = output_item.get("role", "assistant")
                            item_content = output_item.get("content", [])
                        else:
                            message_id = getattr(output_item, "id", None)
                            role = getattr(output_item, "role", "assistant")
                            item_content = (
                                getattr(output_item, "content", [])
                                if hasattr(output_item, "content")
                                else []
                            )

                        # Extract content from the message
                        content = ""
                        content_list = (
                            item_content if isinstance(item_content, (list, tuple)) else []
                        )

                        for content_item in content_list:
                            if content_item is None:
                                continue
                            # Handle both dict and object formats for content items
                            if isinstance(content_item, dict):
                                if "text" in content_item:
                                    content += content_item["text"]
                            elif hasattr(content_item, "text"):
                                content += content_item.text

                        # If we don't have answer_text yet, use this content
                        if not answer_text and content:
                            answer_text = content

                        messages.append(
                            {
                                "role": role,
                                "content": content,
                                "id": message_id,
                                "tool_calls": None,  # responses API handles tools differently
                            }
                        )

                        logger.info(
                            "EXTRACTED MESSAGE ID: %s, content length: %s", message_id, len(content)
                        )

            # Done after every extraction path above, and before the emptiness
            # check below: an answer made of nothing but markers must fall into
            # the fallback rather than be stored as blank text.
            answer_text = strip_citation_markers(answer_text)

            # Final validation - ensure we have some answer text
            if not answer_text:
                logger.warning("No answer text extracted from response, using fallback")
                answer_text = "Unable to extract answer from OpenAI response. Please check the response format."

                # Create fallback assistant message
                messages.append(
                    {"role": "assistant", "content": answer_text, "id": None, "tool_calls": None}
                )
            elif len(messages) == 1:  # Only user message exists but we have answer_text
                logger.warning(
                    "No assistant messages found in response.output, creating fallback with extracted text"
                )
                messages.append(
                    {"role": "assistant", "content": answer_text, "id": None, "tool_calls": None}
                )

            # Structure sources as a proper dict for better organization
            # Ensure sources is a list to avoid issues
            if not isinstance(sources, list):
                logger.warning("Sources is not a list! Type: %s, Value: %s", type(sources), sources)
                sources = []

            # Without citation markers there are no file_citation annotations:
            # the document sources come from the "Documents consulted:" line,
            # checked against what file_search really returned.
            if not any(isinstance(s, dict) and s.get("type") == "file_search" for s in sources):
                search_results = [
                    result
                    for item in (response_dict.get("output") or [])
                    if isinstance(item, dict) and item.get("type") == "file_search_call"
                    for result in (item.get("results") or [])
                ]
                consulted = documents_consulted(answer_text, search_results)
                if (
                    search_results
                    and CONSULTED_LABEL.rstrip(":").lower() not in answer_text.lower()
                ):
                    logger.warning(
                        "Response %s: documents were searched but the answer has no '%s' line, no document source kept",
                        response.id,
                        CONSULTED_LABEL,
                    )
                sources.extend(consulted)

            structured_sources: dict[str, Any] = {
                "files": [
                    s for s in sources if isinstance(s, dict) and s.get("type") == "file_search"
                ],
                "web": [
                    s for s in sources if isinstance(s, dict) and s.get("type") == "web_search"
                ],
                "total_count": len(sources),
            }

            # CRITICAL: Ensure structured_sources is always a dict
            if not isinstance(structured_sources, dict):
                logger.error(
                    "structured_sources is not a dict! Type: %s, Value: %s",
                    type(structured_sources),
                    structured_sources,
                )
                structured_sources = {"files": [], "web": [], "total_count": 0}

            # Special handling for empty sources to ensure proper JSONB storage
            if structured_sources["total_count"] == 0:
                logger.debug("No sources found, using empty dict structure for JSONB")
                structured_sources = {"files": [], "web": [], "total_count": 0}

            logger.info(
                "Final sources: %s total (%s files, %s web)",
                structured_sources["total_count"],
                len(structured_sources["files"]),
                len(structured_sources["web"]),
            )
            logger.debug("Sources structure: %s", structured_sources)

            return {
                "answer": answer_text,
                "sources": structured_sources,  # Structured dict for JSONB storage
                "tokens_used": (response.usage.total_tokens if response.usage else 0)
                + discarded_tokens,
                "response_id": response.id,
                "previous_response_id": previous_response_id,  # Pass through for context chain tracking
                # No confidence_score: it used to be hardcoded to 0.8, which
                # surfaced as "Confidence: 80%" on every answer and in the Excel
                # export -- a number that looked like an assessment but measured
                # nothing. The model states its confidence in prose instead
                # (see the system prompt). The column is gone (migration 0003).
                "processing_time": time.time(),
                "messages": messages,
                "full_response": response.model_dump() if hasattr(response, "model_dump") else {},
            }

        except Exception:
            # The error goes up as it is: the engine classifies it by its class
            # (engine/errors.py), and logs it.
            if "request_params" in locals():
                logger.debug(
                    "Failed request: model %s, %s input messages, %s tools",
                    request_params.get("model", "unknown"),
                    len(request_params.get("input", "")),
                    len(request_params.get("tools", [])),
                )
            raise

    def _build_system_prompt(
        self, company_info: dict[str, Any] | None = None, has_documents: bool = True
    ) -> str:
        """Build the system prompt for due diligence analysis.

        ``has_documents`` says whether a document collection is attached. The
        research rule depends on it: telling the model to search documents that
        do not exist would invite it to imply they were reviewed.
        """

        # Start with role and company context
        prompt = "You are a due diligence expert analyzing company information and documents.\n"

        # Name the two entities separately. A DD question is either about the
        # fund or about the company running it; leaving that implicit makes the
        # model -- and the web search behind it -- guess, which is where answers
        # go wrong. The manager block is skipped when unknown.
        if company_info:
            fund = company_info.get("name") or "the target company"
            prompt += f"\nFUND UNDER REVIEW: {fund}"
            if company_info.get("website_url"):
                prompt += f" ({company_info['website_url']})"

            manager = company_info.get("management_company_name")
            if manager:
                prompt += f"\nMANAGEMENT COMPANY: {manager}"
                if company_info.get("management_company_website"):
                    prompt += f" ({company_info['management_company_website']})"

            if company_info.get("description"):
                prompt += f"\nOverview: {company_info['description']}"

            prompt += (
                "\n\nScope rule: questions marked 'Level: Fund' are about "
                f"{fund} itself (its prospectus, share classes, performance, "
                "portfolio). Questions marked 'Level: Management Company' are "
                "about "
                + (manager if manager else "the company that runs it")
                + " as a firm (its teams, governance, processes, resources). "
                "When a question carries no marker, infer the level from its "
                "wording. Search and cite accordingly: never answer about one "
                "entity when the question is about the other, and never assume "
                "the two share a name.\n"
            )

        # Research rule. Both tools are attached to every question and
        # web_search is forced (settings.tool_choice), but forcing a tool only
        # decides the FIRST call: the model stays free to skip the other one.
        # Measured: under forced web it still skipped the documents on 11 of 72
        # questions, and left free it went to the web on only 7 of 71 -- losing
        # facts about the manager that only public sources (registries, exchange
        # filings) held. The two tools answer different things, so using both is
        # stated as a rule rather than left to judgement.
        if has_documents:
            prompt += """
Research rule -- for EVERY question, use BOTH research tools before answering, to gather as much information as possible and give the most relevant answer. They are complementary and neither is enough on its own:
- Search the provided documents (file_search). The fund's own materials -- prospectus, factsheets, presentations, DDQ -- are the primary source for facts about the fund.
- Search the web (web_search). Regulator registries, exchange filings, press coverage and the manager's website corroborate the documents and cover what they do not describe, in particular the management company's public footprint.
Combine what both return. When a question says where to look, start there, but still check the other source. Say which source supports each key fact, and flag any contradiction between the documents and public sources.
"""
            # Citation format: see CONSULTED_LABEL for why document-citation
            # markers are banned. Web links are left as they are: the holes
            # only ever sit at document citations.
            prompt += f"""
Citation format -- the document search tool's citation markers must NOT appear anywhere in your answer. Name documents in plain words in the text instead (for example: "the Private Placement Memorandum states..."). End the answer with one last line "{CONSULTED_LABEL}" followed by the exact file names of the documents you relied on, as they appear in the search results, separated by semicolons; write "{CONSULTED_LABEL} none" if no document supported the answer. Web sources keep their usual links.
"""
        else:
            prompt += """
Research rule -- no document collection is attached to this review. Search the web (web_search) thoroughly for every question, and state plainly when a fact could only be established from documents the company would have to provide. Never imply that documents were reviewed.
"""

        # Add task and guidelines
        prompt += """
Your task is to provide accurate, detailed answers to due diligence questions based on the provided documents and context.

Guidelines:
- Be thorough and analytical in your responses
- Cite specific sources when possible
- If information is not available, clearly state this
- Provide confidence levels where appropriate
- Focus on factual, objective analysis
- Consider regulatory and compliance implications

CRITICAL Formatting Requirements:
Format your answers like a professional analyst responding to specific due diligence questions.
"""

        return prompt

    def build_summary_request_params(
        self,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int = 6000,
    ) -> dict[str, Any]:
        """Build the request body for a summary call, with NO tools.

        Shared by the synchronous path (generate_summary) and the Batch path,
        which sends this very body as the 'body' of a JSONL line, so that the
        two cannot drift apart.
        """
        request_params = {
            "model": self.model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
            "store": True,
        }
        self._apply_model_params(
            request_params,
            temperature=0.2,
            max_output_tokens=max_output_tokens,
            reasoning_effort=settings.summary_reasoning_effort,
        )
        return request_params

    @staticmethod
    def extract_output_text(response_dict: dict[str, Any]) -> str:
        """Pull the assistant text out of a Responses payload in dict form.

        Works on both a model_dump() of the SDK object and the raw body a Batch
        output line carries, which is a plain dict with no 'output_text' helper.
        """
        text = response_dict.get("output_text")
        if text:
            return text

        parts = []
        for item in response_dict.get("output", []) or []:
            if item.get("type") == "message":
                for c in item.get("content", []) or []:
                    if isinstance(c, dict) and c.get("text"):
                        parts.append(c["text"])
        return "".join(parts)

    def generate_summary(
        self,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int = 6000,
    ) -> str:
        """Generate a plain-text summary/synthesis with NO tools.

        Used for section summaries and the DD-type synthesis: the content has
        already been retrieved (the answers), so we only need the model to
        rewrite/synthesize it. No file_search / web_search, no response chaining.
        Returns the generated text (empty string on no output).
        """
        request_params = self.build_summary_request_params(
            system_prompt, user_prompt, max_output_tokens
        )

        response = self.client.responses.create(**request_params)
        if response is None:
            raise ResponseError("OpenAI API returned None response for summary")

        text = getattr(response, "output_text", None)
        if text:
            return text

        # Fallback: walk the output array for message text
        try:
            response_dict = response.model_dump() if hasattr(response, "model_dump") else {}
            return self.extract_output_text(response_dict)
        except Exception as e:
            logger.error("Failed to extract summary text: %s", e)
            return ""

    # === Batch API (summaries only) ==========================================
    #
    # Batch bills at half the synchronous rate. Its only completion window is
    # 24h, and summarising happens in two stages -- N section summaries, then one
    # synthesis built from them -- so batching both would chain two 24h windows.
    # Only stage 1 goes through Batch; the single final synthesis stays
    # synchronous. web_search is refused in Batch, which is why the question
    # engine itself cannot use it.

    def submit_summary_batch(
        self,
        requests: list[dict[str, Any]],
        description: str = "",
    ) -> dict[str, Any]:
        """Upload a JSONL of /v1/responses requests and enqueue them as a batch.

        'requests' are {custom_id, body} pairs; custom_id is what maps a result
        line back to its section, since output order does not follow input order.
        Returns the batch id, the uploaded file id and the initial status.
        """
        lines = [
            json.dumps(
                {
                    "custom_id": req["custom_id"],
                    "method": "POST",
                    "url": "/v1/responses",
                    "body": req["body"],
                },
                ensure_ascii=False,
            )
            for req in requests
        ]
        payload = ("\n".join(lines) + "\n").encode("utf-8")

        upload = self.client.files.create(
            file=("summary_batch.jsonl", BytesIO(payload)),
            purpose="batch",
        )
        batch = self.client.batches.create(
            input_file_id=upload.id,
            endpoint="/v1/responses",
            completion_window="24h",
            metadata={"description": description[:512]} if description else None,
        )
        logger.info(
            "Submitted summary batch %s (%s requests, status=%s)",
            batch.id,
            len(requests),
            batch.status,
        )
        return {
            "batch_id": batch.id,
            "input_file_id": upload.id,
            "status": batch.status,
        }

    def get_batch(self, batch_id: str) -> dict[str, Any]:
        """Current state of a batch: status, output/error file ids, counts."""
        batch = self.client.batches.retrieve(batch_id)
        counts = getattr(batch, "request_counts", None)
        return {
            "batch_id": batch.id,
            "status": batch.status,
            "output_file_id": getattr(batch, "output_file_id", None),
            "error_file_id": getattr(batch, "error_file_id", None),
            "completed": getattr(counts, "completed", None) if counts else None,
            "failed": getattr(counts, "failed", None) if counts else None,
            "total": getattr(counts, "total", None) if counts else None,
        }

    def cancel_batch(self, batch_id: str) -> dict[str, Any]:
        """Ask OpenAI to cancel a batch; returns its state right after.

        Cancelling is not instantaneous: the batch goes to 'cancelling', then
        'cancelled' within minutes. Only the requests not yet completed are
        dropped -- those already done stay billed. The frontend keeps polling
        through 'cancelling', which is why that status counts as pending.
        """
        batch = self.client.batches.cancel(batch_id)
        logger.info("Cancel requested for summary batch %s (status=%s)", batch.id, batch.status)
        counts = getattr(batch, "request_counts", None)
        return {
            "batch_id": batch.id,
            "status": batch.status,
            "completed": getattr(counts, "completed", None) if counts else None,
            "total": getattr(counts, "total", None) if counts else None,
        }

    def fetch_batch_texts(self, output_file_id: str) -> dict[str, str]:
        """Download a completed batch's output and map custom_id -> text.

        Output order does not follow input order, hence the mapping. A line that
        did not return 200 is logged and skipped rather than raising: one failed
        section should not lose the others.
        """
        content = self.client.files.content(output_file_id)
        raw = content.read() if hasattr(content, "read") else content.content
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")

        texts: dict[str, str] = {}
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                logger.error("Unparsable batch output line: %s", e)
                continue

            custom_id = record.get("custom_id")
            if not custom_id:
                continue

            if record.get("error"):
                logger.error("Batch request %s errored: %s", custom_id, record["error"])
                continue

            response = record.get("response") or {}
            if response.get("status_code") != 200:
                logger.error(
                    "Batch request %s returned status %s", custom_id, response.get("status_code")
                )
                continue

            texts[custom_id] = self.extract_output_text(response.get("body") or {})

        return texts

    # === Vector Store Management Methods ===

    def get_vector_store_info(self, vector_store_id: str) -> dict[str, Any]:
        """Get detailed information about a vector store including expiration"""
        try:
            logger.info("Retrieving vector store info for: %s", vector_store_id)
            vector_store = self.client.vector_stores.retrieve(vector_store_id)
            logger.debug("Raw vector store object: %s", vector_store)

            # Extract expiration information safely
            expires_at = None
            expires_after_days = None

            try:
                if hasattr(vector_store, "expires_after") and vector_store.expires_after:
                    if hasattr(vector_store.expires_after, "days"):
                        expires_after_days = vector_store.expires_after.days
                    elif isinstance(vector_store.expires_after, dict):
                        expires_after_days = vector_store.expires_after.get("days")

                    # Calculate expires_at based on last_active_at + days
                    if (
                        expires_after_days
                        and hasattr(vector_store, "last_active_at")
                        and vector_store.last_active_at
                    ):
                        try:
                            last_active = datetime.fromtimestamp(
                                vector_store.last_active_at, tz=UTC
                            )
                            expires_at = last_active + timedelta(days=expires_after_days)
                        except (ValueError, OSError) as dt_error:
                            logger.warning("Error calculating expires_at: %s", dt_error)
            except Exception as exp_error:
                logger.warning(
                    "Error processing expiration info for %s: %s", vector_store_id, exp_error
                )

            # Handle file_counts safely - it can be an object or dict
            file_counts_dict = {}
            try:
                file_counts_obj = getattr(vector_store, "file_counts", None)
                logger.debug(
                    "File counts object: %s (type: %s)", file_counts_obj, type(file_counts_obj)
                )

                if file_counts_obj:
                    # If it's already a dict, use it directly
                    if isinstance(file_counts_obj, dict):
                        file_counts_dict = file_counts_obj
                    else:
                        # If it's an object, extract attributes
                        if hasattr(file_counts_obj, "total"):
                            file_counts_dict["total"] = getattr(file_counts_obj, "total", 0)
                        if hasattr(file_counts_obj, "in_progress"):
                            file_counts_dict["in_progress"] = getattr(
                                file_counts_obj, "in_progress", 0
                            )
                        if hasattr(file_counts_obj, "completed"):
                            file_counts_dict["completed"] = getattr(file_counts_obj, "completed", 0)
                        if hasattr(file_counts_obj, "failed"):
                            file_counts_dict["failed"] = getattr(file_counts_obj, "failed", 0)
                        if hasattr(file_counts_obj, "cancelled"):
                            file_counts_dict["cancelled"] = getattr(file_counts_obj, "cancelled", 0)

                        # Ensure total is calculated if not present
                        if "total" not in file_counts_dict:
                            file_counts_dict["total"] = (
                                file_counts_dict.get("completed", 0)
                                + file_counts_dict.get("in_progress", 0)
                                + file_counts_dict.get("failed", 0)
                                + file_counts_dict.get("cancelled", 0)
                            )
            except Exception as file_count_error:
                logger.warning(
                    "Error processing file_counts for %s: %s", vector_store_id, file_count_error
                )
                file_counts_dict = {"total": 0}

            # Safely extract other fields
            result = {
                "id": getattr(vector_store, "id", vector_store_id),
                "name": getattr(vector_store, "name", f"Vector Store {vector_store_id[:8]}"),
                "status": getattr(vector_store, "status", "unknown"),
                "file_counts": file_counts_dict,
                "usage_bytes": getattr(vector_store, "usage_bytes", 0),
                "expires_after_days": expires_after_days,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "last_active_at": getattr(vector_store, "last_active_at", None),
                "created_at": getattr(vector_store, "created_at", None),
            }

            logger.debug("Processed vector store info for %s: %s", vector_store_id, result)
            return result

        except Exception as e:
            logger.error("Error retrieving vector store info for %s: %s", vector_store_id, e)
            logger.error("Exception type: %s", type(e))
            raise

    def update_vector_store_name(self, vector_store_id: str, name: str) -> bool:
        """Update the name of a vector store"""
        try:
            self.client.vector_stores.update(vector_store_id, name=name)
            return True
        except Exception as e:
            logger.error("Error updating vector store name: %s", e)
            raise

    def list_vector_store_files(self, vector_store_id: str) -> list[dict[str, Any]]:
        """List all files in a vector store with detailed information including attributes"""
        try:
            files = self.client.vector_stores.files.list(vector_store_id=vector_store_id, limit=100)

            def fetch_file_details(file_obj):
                try:
                    file_details = self.client.files.retrieve(file_obj.id)
                    return {
                        "id": file_obj.id,
                        "filename": file_details.filename,
                        "size_bytes": file_details.bytes,
                        "created_at": file_details.created_at,
                        "status": getattr(file_obj, "status", "completed"),
                        "usage_bytes": getattr(file_obj, "usage_bytes", 0),
                        "attributes": getattr(file_obj, "attributes", {}),
                        "last_error": file_obj.last_error.model_dump()
                        if hasattr(file_obj, "last_error") and file_obj.last_error
                        else None,
                    }
                except Exception as file_error:
                    logger.warning("Could not get details for file %s: %s", file_obj.id, file_error)
                    # No name, size nor date: the interface says so, and the
                    # listing is not cached (services/vector_stores.list_files).
                    return {
                        "id": file_obj.id,
                        "filename": f"File {file_obj.id}",
                        "details_missing": True,
                        "status": getattr(file_obj, "status", "unknown"),
                        "attributes": getattr(file_obj, "attributes", {}),
                        "last_error": file_obj.last_error.model_dump()
                        if hasattr(file_obj, "last_error") and file_obj.last_error
                        else None,
                    }

            # One request per file: run them side by side.
            with ThreadPoolExecutor(max_workers=8) as pool:
                return list(pool.map(fetch_file_details, files.data))
        except Exception as e:
            logger.error("Error listing vector store files: %s", e)
            raise

    def remove_file_from_vector_store(self, vector_store_id: str, file_id: str) -> bool:
        """Remove a file from a vector store"""
        try:
            self.client.vector_stores.files.delete(vector_store_id=vector_store_id, file_id=file_id)
            return True
        except Exception as e:
            logger.error("Error removing file from vector store: %s", e)
            raise

    def delete_vector_store(self, vector_store_id: str) -> bool:
        """Delete a vector store entirely"""
        try:
            self.client.vector_stores.delete(vector_store_id)
            return True
        except Exception as e:
            logger.error("Error deleting vector store: %s", e)
            raise

    def delete_file(self, file_id: str) -> bool:
        """Delete a file from OpenAI completely"""
        try:
            self.client.files.delete(file_id)
            return True
        except Exception as e:
            logger.error("Error deleting file: %s", e)
            raise

    def get_file(self, file_id: str) -> dict[str, Any]:
        """Retrieve file information including expiration details"""
        try:
            file_obj = self.client.files.retrieve(file_id)
            return {
                "id": file_obj.id,
                "object": file_obj.object,
                "bytes": file_obj.bytes,
                "created_at": file_obj.created_at,
                "expires_at": getattr(file_obj, "expires_at", None),
                "filename": file_obj.filename,
                "purpose": file_obj.purpose,
                "status": getattr(file_obj, "status", "unknown"),
            }
        except Exception as e:
            logger.error("Error retrieving file %s: %s", file_id, e)
            raise
