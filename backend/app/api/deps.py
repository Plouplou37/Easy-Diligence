"""Dependencies shared by the routers: the one place a request's user is resolved.

Every endpoint that needs a user goes through get_current_active_user (alias
get_current_user) or the admin variant built on it: the token is decoded here
only, and an inactive account is refused here only.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.dd_types import DDType
from app.models.session import DDSession
from app.models.user import User as UserModel
from app.services.auth import get_user, is_admin
from app.services.dd_types import get_dd_type_by_code
from app.services.sessions import get_session_for_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_active_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserModel:
    """The authenticated, active user of the request."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(token, token_type="access")
    if not payload:
        raise credentials_exception

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.isdigit():
        raise credentials_exception
    user_id = int(subject)

    user = get_user(db, user_id)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return user


# Shorter name for the same dependency.
get_current_user = get_current_active_user


def get_current_admin_user(
    current_user: UserModel = Depends(get_current_active_user),
) -> UserModel:
    """The current user, if they are an admin."""
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def get_accessible_session(
    session_identifier: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
) -> DDSession:
    """The session of the `{session_identifier}` path parameter (an id or a
    session code), if the user may access it: 404 if unknown, 403 if not theirs."""
    return get_session_for_user(db, session_identifier, current_user)


def get_visible_dd_type(
    dd_type: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
) -> DDType:
    """The DD type of the `{dd_type}` path parameter (its code), if the user may see it."""
    return get_dd_type_by_code(db, dd_type, current_user)
