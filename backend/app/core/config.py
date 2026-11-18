from typing import Literal

from pydantic import SecretStr, field_validator

from app.core.database_settings import (  # noqa: F401  (ConfigurationError re-exported)
    ConfigurationError,
    DatabaseSettings,
    load_settings,
)

# Shortest JWT signing key accepted: 32 characters. `openssl rand -hex 32`
# gives 64.
_JWT_SECRET_MIN_LENGTH = 32


class Settings(DatabaseSettings):
    # --- Required secrets: no default, the application refuses to start
    # without them. SecretStr keeps them out of logs and reprs.
    openai_api_key: SecretStr
    jwt_secret_key: SecretStr

    # OpenAI
    openai_model: str = "gpt-4o"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # App
    app_name: str = "Easy Diligence"
    debug: bool = False
    # Level of the application's own logs (third-party libraries: WARNING and up).
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    # Interactive API docs (/docs, /redoc, /openapi.json). Off unless asked for:
    # they describe every endpoint to whoever can reach the server.
    docs_enabled: bool = False

    # JWT Authentication
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Login throttling: after this many failed attempts within the window, the
    # account (and, at a higher count, the client address) is refused with a
    # 429 until the window has passed. Kept in memory, per backend process.
    login_max_attempts: int = 5
    login_window_seconds: int = 900

    # CORS
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://localhost:5178",
        "http://localhost:5179",
        "http://localhost:3000",
    ]

    # Rate limiting between questions.
    # Measured on the account: 10 000 requests/min and 10 000 000 tokens/min,
    # while a run uses ~0.5 request/min. No pause is needed, and 429s are already
    # handled by the processor's exponential backoff + circuit breaker. These
    # knobs remain as an escape hatch: 0 disables the rule it belongs to.
    inter_question_delay_seconds: int = 0  # pause after every question
    max_questions_per_batch: int = 6  # batch size for the batch pause
    batch_sleep_minutes: int = 0  # pause after each batch
    high_token_sleep_seconds: int = 0  # pause after a heavy question
    token_threshold: int = 50000  # what counts as "heavy" (was 3000,
    # unreachable: a question costs 8k-46k)

    # Server-side compaction of the conversation chain (reasoning models only).
    # Chaining grows the input by ~4 200 tokens per question, so a 292-question
    # DD would reach ~1.24M tokens and blow past the 1.05M context window: from
    # roughly question 247 truncation="auto" starts silently dropping the start
    # of the DD. Compaction compresses that history instead of discarding it.
    # 0 disables it. Verified as accepted and validated by gpt-5.6-luna.
    compact_threshold: int = 200000

    # Reasoning effort, on reasoning models only (see openai_client). Accepted
    # values on gpt-5.6-luna: none, low, medium, high, xhigh, max. Reasoning
    # tokens are billed as output and eat into max_output_tokens, so raising
    # this costs both money and latency.
    #   - questions: extraction from documents already retrieved. "low" is the
    #     measured reference (a 72-question run with no failure, most answers
    #     grounded in the documents). Left alone so runs stay comparable to it.
    #   - summaries: no retrieval at all, only drafting and ranking from answers
    #     already produced -- the case where more reasoning actually helps. The
    #     Batch API's 50% discount roughly pays for the extra tokens.
    reasoning_effort: str = "low"
    summary_reasoning_effort: str = "medium"

    # Which tool the model is made to call first when answering a question.
    # Both tools (file_search on the assigned vector stores, web_search) are
    # always attached; this only decides whether one of them is imposed.
    #   "web_search" -> a web search is forced on EVERY question before the
    #                   model may do anything else. The default, by measurement.
    #   "auto"       -> the model picks.
    #   "none"       -> send nothing at all, leaving the API to its own default.
    #
    # Why web_search by default: an A/B run on the same questionnaire and the
    # same documents showed that "auto" barely saves input tokens (the chained
    # conversation dominates the input, not the search results) but makes the
    # model skip the web on most questions. Answers lose their web citations,
    # more of them come back with no source at all, and questions about the
    # management company suffer most: the fund documents describe the fund,
    # while the manager's public footprint only exists on the web.
    tool_choice: str = "web_search"

    # File uploads (vector store documents, regeneration attachments). Size in
    # bytes; extensions lowercase, without the dot.
    max_upload_size: int = 104857600  # 100 MB
    allowed_extensions: list[str] = [
        "pdf",
        "doc",
        "docx",
        "pptx",
        "txt",
        "md",
        "html",
        "json",
        "csv",
        "xls",
        "xlsx",
    ]

    # Email Configuration
    smtp_hostname: str = "smtp.office365.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    mail_from: str = ""
    mail_from_name: str = "Easy Diligence"

    # Frontend URL for password reset links
    frontend_url: str = "http://localhost:5173"

    # Optional banner image at the top of exported PDF reports (PNG or JPEG).
    # Empty means no banner; a path to a missing file is logged and ignored.
    brand_banner_path: str = ""

    @field_validator("openai_api_key")
    @classmethod
    def _not_empty(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("jwt_secret_key")
    @classmethod
    def _jwt_secret_strong_enough(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().strip()) < _JWT_SECRET_MIN_LENGTH:
            raise ValueError(
                f"must be at least {_JWT_SECRET_MIN_LENGTH} characters "
                "(generate one with: openssl rand -hex 32)"
            )
        return value

    @field_validator("allowed_extensions")
    @classmethod
    def _normalise_extensions(cls, value: list[str]) -> list[str]:
        return [ext.lower().lstrip(".") for ext in value]

    @field_validator("log_level", mode="before")
    @classmethod
    def _upper_log_level(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


settings = load_settings(Settings)
