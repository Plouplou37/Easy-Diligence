"""Administration commands: `uv run python -m app.cli --help`.

With Docker: `docker compose exec backend python -m app.cli <command>`.
"""

import re

import typer
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError, ProgrammingError

import app.models  # noqa: F401  (registers every mapper before the first query)
from app.core.database import SessionLocal
from app.core.exceptions import ConflictError
from app.models.user import UserCreate
from app.services.auth import create_user

cli = typer.Typer(help="Easy Diligence administration commands.", no_args_is_help=True)


@cli.callback()
def main() -> None:
    """Easy Diligence administration commands."""


def _username_from_email(email: str) -> str:
    """'jane.doe+dd@example.com' -> 'jane.doe-dd' (the username rules: 3 to 30
    of letters, digits, '.', '_' and '-')."""
    local = re.sub(r"[^a-zA-Z0-9._-]", "-", email.split("@", 1)[0])[:30]
    return local if len(local) >= 3 else f"{local}-admin"[:30]


@cli.command("create-admin")
def create_admin(
    email: str = typer.Argument(..., help="Email address, used to log in."),
    full_name: str = typer.Argument(..., help='Full name, e.g. "Jane Doe".'),
    username: str | None = typer.Option(
        None, help="Username. Default: the part of the email before '@'."
    ),
) -> None:
    """Create an administrator account. The password is asked for, never passed
    as an argument (it would stay in the shell history)."""
    password = typer.prompt("Password", hide_input=True, confirmation_prompt=True)

    try:
        user_create = UserCreate(
            email=email,
            username=username or _username_from_email(email),
            full_name=full_name,
            password=password,
            role="admin",
        )
    except ValidationError as exc:
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"])
            typer.echo(f"Invalid {field}: {error['msg']}", err=True)
        raise typer.Exit(code=1) from None

    db = SessionLocal()
    try:
        user = create_user(db, user_create, password=user_create.password, role="admin")
    except ConflictError as exc:
        typer.echo(f"Error: {exc.message}", err=True)
        raise typer.Exit(code=1) from None
    except (OperationalError, ProgrammingError):
        typer.echo(
            "Error: the database cannot be reached, or its tables do not exist yet. "
            "Create them with: uv run alembic upgrade head",
            err=True,
        )
        raise typer.Exit(code=1) from None
    finally:
        db.close()

    typer.echo(f"Administrator created: {user.email} (username {user.username}, id {user.id})")


if __name__ == "__main__":
    cli()
