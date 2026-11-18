"""
Utility functions for common operations
"""
import re
import secrets
import string

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.session import DDSession


def build_company_info(company) -> dict:
    """Context describing the DD subject, as handed to the model.

    Carries the fund AND its management company as two distinct entities: the
    questionnaires ask about both, and without the distinction the model -- and
    the web search behind it -- has to guess which one a question targets.

    Single source of truth for the three call sites (start, resume, regenerate)
    so a new field reaches all of them at once. Returns {} when there is no
    company, which _build_system_prompt handles.
    """
    if company is None:
        return {}
    return {
        "name": company.name,
        "website_url": getattr(company, "website_url", None),
        "description": getattr(company, "description", None),
        "management_company_name": getattr(company, "management_company_name", None),
        "management_company_website": getattr(company, "management_company_website", None),
    }


def get_session_by_identifier(db: Session, session_identifier: str) -> tuple[DDSession, int]:
    """
    Get session by ID or session code.

    Args:
        db: Database session
        session_identifier: Either integer ID or session code string

    Returns:
        tuple: (session_object, session_id)

    Raises:
        HTTPException: If session not found
    """
    # Try to parse as integer ID first
    try:
        session_id = int(session_identifier)
        session = db.query(DDSession).filter(DDSession.id == session_id).first()
    except ValueError:
        # Not an integer, treat as session_code
        session = db.query(DDSession).filter(DDSession.session_code == session_identifier).first()
        session_id = session.id if session else None

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session, session_id


def normalize_status(status: str) -> str:
    """
    Normalize status string to lowercase for consistent styling.

    Args:
        status: Status string (may be uppercase or lowercase)

    Returns:
        str: Lowercase status string
    """
    return status.lower() if status else ""


def format_status_for_api(status: str) -> str:
    """
    Format status string for API calls (uppercase).

    Args:
        status: Status string (may be uppercase or lowercase)

    Returns:
        str: Uppercase status string
    """
    return status.upper() if status else ""


def validate_email(email: str) -> bool:
    """
    Validate email address format.

    Args:
        email: Email string to validate

    Returns:
        bool: True if valid email format, False otherwise
    """
    if not email:
        return False

    # Basic email regex pattern (doesn't allow leading dot)
    email_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))


def generate_unique_code(name: str, user_id: int) -> str:
    """
    Generate a unique code based on name and user ID.

    Args:
        name: Name to use in code generation
        user_id: User ID to include in code

    Returns:
        str: Generated unique code
    """
    # Take first 3 letters of name (uppercase)
    name_part = ''.join(name.split())[:3].upper()
    if not name_part:
        name_part = 'GEN'

    # Add user identifier
    user_part = str(user_id)[-2:].zfill(2)

    # Add random suffix for uniqueness
    random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))

    # Combine: NAME-USER-RANDOM
    return f"{name_part}-{user_part}-{random_part}"
