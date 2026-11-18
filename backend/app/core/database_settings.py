"""The database settings, and how every settings class is loaded.

Kept apart from config.py, which builds the full application settings as soon
as it is imported: Alembic imports this module only, so running a migration
needs the database connection and nothing else (no OpenAI key, no JWT key).
"""

from pathlib import Path

from pydantic import SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

# backend/.env, wherever the process is started from. Environment variables
# win over this file (that is how Docker and the tests configure the app).
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class ConfigurationError(RuntimeError):
    """The settings are missing or invalid; the message lists every problem."""


class DatabaseSettings(BaseSettings):
    """The database connection alone."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # PostgreSQL: either DATABASE_URL, or the POSTGRES_* parts (the ones the
    # PostgreSQL image reads too). DATABASE_URL wins when set.
    # Form: postgresql+psycopg://<user>:<password>@<host>:5432/<database>
    database_url: SecretStr | None = None
    postgres_user: str | None = None
    postgres_password: SecretStr | None = None
    postgres_db: str | None = None
    postgres_host: str = "db"  # the database service of docker compose
    postgres_port: int = 5432

    @field_validator("database_url", "postgres_password", mode="before")
    @classmethod
    def _blank_is_unset(cls, value: object) -> object:
        # An empty line in .env (DATABASE_URL=) means "not set".
        return None if isinstance(value, str) and not value.strip() else value

    @model_validator(mode="after")
    def _database_configured(self) -> "DatabaseSettings":
        if self.database_url is None and not (
            self.postgres_user and self.postgres_password and self.postgres_db
        ):
            raise ValueError(
                "no database configured: set DATABASE_URL, or POSTGRES_USER, "
                "POSTGRES_PASSWORD and POSTGRES_DB"
            )
        return self

    @property
    def sqlalchemy_database_url(self) -> str:
        """The URL the engine and Alembic connect with (contains the password)."""
        if self.database_url is not None:
            return self.database_url.get_secret_value()
        assert self.postgres_password is not None  # checked by _database_configured
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)


def load_settings[S: BaseSettings](settings_class: type[S]) -> S:
    """Build a settings class, turning a validation failure into one clear message."""
    try:
        return settings_class()
    except ValidationError as exc:
        problems = []
        for error in exc.errors():
            name = ".".join(str(part) for part in error["loc"]).upper() or "DATABASE"
            reason = "required" if error["type"] == "missing" else error["msg"]
            problems.append(f"  - {name}: {reason}")
        raise ConfigurationError(
            "Invalid configuration. Set these variables in backend/.env or in the "
            "environment (see .env.template):\n" + "\n".join(problems)
        ) from None
