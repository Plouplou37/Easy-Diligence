from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.core.security import (
    get_password_hash,
    hash_token,
    refresh_token_expiry,
    verify_password,
)
from app.models.user import User, UserSession
from app.schemas.user import Role, UserProfile


def _now() -> datetime:
    return datetime.now(UTC)


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None

    # Update last login
    user.last_login = _now()
    db.commit()

    return user


def create_user(db: Session, profile: UserProfile, password: str, role: Role = "analyst") -> User:
    """Create a user. The role is the caller's decision, never the request's:
    self-registration always passes the default."""
    existing_user = db.query(User).filter(
        (User.email == profile.email) | (User.username == profile.username)
    ).first()

    if existing_user:
        if existing_user.email == profile.email:
            raise ConflictError("Email already registered")
        raise ConflictError("Username already taken")

    db_user = User(
        email=profile.email,
        username=profile.username,
        password_hash=get_password_hash(password),
        full_name=profile.full_name,
        company=profile.company,
        phone=profile.phone,
        role=role,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def get_user(db: Session, user_id: int) -> User | None:
    """Get a user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Get a user by email."""
    return db.query(User).filter(User.email == email).first()


def update_user(db: Session, user_id: int, user_update: dict) -> User | None:
    """Update user information."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    for field, value in user_update.items():
        if value is not None:
            setattr(user, field, value)

    user.updated_at = _now()
    db.commit()
    db.refresh(user)

    return user


def change_password(db: Session, user_id: int, current_password: str, new_password: str) -> bool:
    """Change user password."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False

    if not verify_password(current_password, user.password_hash):
        return False

    user.password_hash = get_password_hash(new_password)
    user.updated_at = _now()
    db.commit()

    return True


def set_password(db: Session, user: User, new_password: str) -> None:
    """Replace a user's password (reset flow). Invalidates outstanding reset
    tokens too: they carry a fingerprint of the old password hash."""
    user.password_hash = get_password_hash(new_password)
    user.updated_at = _now()
    db.commit()


def create_user_session(db: Session, user_id: int, access_token: str, refresh_token: str,
                        ip_address: str | None = None,
                        user_agent: str | None = None) -> UserSession:
    """Record a login. Only the tokens' SHA-256 is stored."""
    session = UserSession(
        user_id=user_id,
        access_token_hash=hash_token(access_token),
        refresh_token_hash=hash_token(refresh_token),
        expires_at=refresh_token_expiry(),
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def rotate_user_session(db: Session, old_refresh_token: str,
                        access_token: str, refresh_token: str) -> bool:
    """Swap a session's tokens after a refresh. False if the session is gone."""
    session = db.query(UserSession).filter(
        UserSession.refresh_token_hash == hash_token(old_refresh_token)
    ).first()
    if not session:
        return False
    session.access_token_hash = hash_token(access_token)
    session.refresh_token_hash = hash_token(refresh_token)
    session.expires_at = refresh_token_expiry()
    db.commit()
    return True


def invalidate_user_sessions(db: Session, user_id: int) -> None:
    """Invalidate all sessions for a user (logout from all devices)."""
    db.query(UserSession).filter(UserSession.user_id == user_id).delete()
    db.commit()


def validate_refresh_token(db: Session, refresh_token: str) -> User | None:
    """Return the user of a live session holding this refresh token."""
    session = db.query(UserSession).filter(
        UserSession.refresh_token_hash == hash_token(refresh_token),
        UserSession.expires_at > _now(),
    ).first()

    if not session:
        return None

    return db.query(User).filter(User.id == session.user_id).first()


# Admin functions
def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[User], int]:
    """Get all users with pagination. Returns (users, total_count)."""
    total = db.query(User).count()
    users = db.query(User).offset(skip).limit(limit).all()
    return users, total


def update_user_role(db: Session, user_id: int, new_role: Role) -> bool:
    """Update user role. Returns True if successful."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False

    user.role = new_role
    user.updated_at = _now()
    db.commit()
    return True


def update_user_status(db: Session, user_id: int, is_active: bool) -> bool:
    """Update user active status. Returns True if successful."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False

    user.is_active = is_active
    user.updated_at = _now()
    db.commit()
    return True


def is_admin(user: User) -> bool:
    """Check if user has admin role."""
    return user.role == "admin"
