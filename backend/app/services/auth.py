from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserSession
from app.schemas.user import UserCreate
from app.core.security import verify_password, get_password_hash, create_tokens

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user

def create_user(db: Session, user_create: UserCreate) -> User:
    """Create a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_create.email) | (User.username == user_create.username)
    ).first()
    
    if existing_user:
        if existing_user.email == user_create.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Create new user
    db_user = User(
        email=user_create.email,
        username=user_create.username,
        password_hash=get_password_hash(user_create.password),
        full_name=user_create.full_name,
        company=user_create.company,
        phone=user_create.phone,
        role=user_create.role
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

def get_user(db: Session, user_id: int) -> Optional[User]:
    """Get a user by ID."""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get a user by email."""
    return db.query(User).filter(User.email == email).first()

def update_user(db: Session, user_id: int, user_update: dict) -> Optional[User]:
    """Update user information."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    for field, value in user_update.items():
        if value is not None:
            setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
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
    user.updated_at = datetime.utcnow()
    db.commit()
    
    return True

def create_user_session(db: Session, user_id: int, access_token: str, refresh_token: str, 
                       ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> UserSession:
    """Create a user session record."""
    # Calculate expiry time
    expires_at = datetime.utcnow() + timedelta(days=7)  # Refresh token expiry
    
    session = UserSession(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session

def invalidate_user_sessions(db: Session, user_id: int) -> None:
    """Invalidate all sessions for a user (logout from all devices)."""
    db.query(UserSession).filter(UserSession.user_id == user_id).delete()
    db.commit()

def validate_refresh_token(db: Session, refresh_token: str) -> Optional[User]:
    """Validate a refresh token and return the user."""
    session = db.query(UserSession).filter(
        UserSession.refresh_token == refresh_token,
        UserSession.expires_at > datetime.utcnow()
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

def update_user_role(db: Session, user_id: int, new_role: str) -> bool:
    """Update user role. Returns True if successful."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    user.role = new_role
    user.updated_at = datetime.utcnow()
    db.commit()
    return True

def update_user_status(db: Session, user_id: int, is_active: bool) -> bool:
    """Update user active status. Returns True if successful."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    user.is_active = is_active
    user.updated_at = datetime.utcnow()
    db.commit()
    return True

def is_admin(user: User) -> bool:
    """Check if user has admin role."""
    return user.role == "admin"