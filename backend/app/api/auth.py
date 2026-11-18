from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.schemas.user import (
    UserCreate, UserLogin, UserRegister, User, Token,
    UserUpdate, PasswordChange, PasswordReset, PasswordResetConfirm
)
from app.core.auth import (
    authenticate_user, create_user, get_user, get_user_by_email,
    update_user, change_password, create_user_session,
    invalidate_user_sessions, validate_refresh_token
)
from app.core.security import create_tokens, verify_token, decode_token, create_password_reset_token, verify_password_reset_token, get_password_hash
from app.core.email import email_service
from app.models.user import UserSession, User as UserModel

logger = logging.getLogger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    user_create: UserRegister,
    request: Request,
    db: Session = Depends(get_db)
):
    """Register a new user."""
    # Create the user
    user = create_user(db, user_create)
    
    return user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Login and receive access token."""
    user = authenticate_user(db, form_data.username, form_data.password)  # username is email in our case
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Create tokens
    tokens = create_tokens(user.id, user.email, user.role)
    
    # Store session
    ip_address = request.client.host if request else None
    user_agent = request.headers.get("User-Agent") if request else None
    create_user_session(
        db, user.id, tokens["access_token"], tokens["refresh_token"],
        ip_address, user_agent
    )
    
    return tokens

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    # Verify refresh token
    payload = verify_token(refresh_token, token_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate refresh token in database
    user = validate_refresh_token(db, refresh_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create new tokens
    tokens = create_tokens(user.id, user.email, user.role)
    
    # Update session with new tokens
    session = db.query(UserSession).filter(UserSession.refresh_token == refresh_token).first()
    if session:
        session.access_token = tokens["access_token"]
        session.refresh_token = tokens["refresh_token"]
        session.expires_at = datetime.utcnow() + timedelta(days=7)
        db.commit()
    
    return tokens

@router.get("/me", response_model=User)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Get current user information."""
    # Verify token
    payload = verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = int(payload.get("sub"))
    user = get_user(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

@router.put("/profile", response_model=User)
async def update_profile(
    user_update: UserUpdate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Update user profile."""
    # Verify token
    payload = verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = int(payload.get("sub"))
    
    # Update user
    updated_user = update_user(db, user_id, user_update.dict(exclude_unset=True))
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return updated_user

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Logout and invalidate tokens."""
    # Verify token
    payload = verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = int(payload.get("sub"))
    
    # Invalidate all user sessions
    invalidate_user_sessions(db, user_id)
    
    return {"detail": "Successfully logged out"}

@router.put("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_user_password(
    password_change: PasswordChange,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Change user password."""
    # Verify token
    payload = verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = int(payload.get("sub"))
    
    # Change password
    success = change_password(
        db, user_id, 
        password_change.current_password, 
        password_change.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Invalidate all sessions after password change
    invalidate_user_sessions(db, user_id)
    
    return {"detail": "Password changed successfully. Please login again."}

@router.post("/reset-password", status_code=status.HTTP_202_ACCEPTED)
async def reset_password_request(
    password_reset: PasswordReset,
    db: Session = Depends(get_db)
):
    """Request password reset."""
    # Check if user exists
    user = get_user_by_email(db, password_reset.email)
    
    # Always return success to prevent email enumeration
    if user and user.is_active:
        try:
            # Generate reset token
            reset_token = create_password_reset_token(user.email)
            
            # Send password reset email
            email_sent = await email_service.send_password_reset_email(
                to_email=user.email,
                reset_token=reset_token,
                user_name=user.full_name or ""
            )
            
            if not email_sent:
                # Log the error but don't reveal it to prevent email enumeration
                logger.error(f"Failed to send password reset email to {user.email}")
                
        except Exception as e:
            logger.error(f"Error sending password reset email: {str(e)}")
    else:
        logger.info(f"Password reset requested for non-existent or inactive user: {password_reset.email}")
    
    return {"detail": "If the email exists, a password reset link has been sent."}

@router.post("/reset-password-confirm", status_code=status.HTTP_200_OK)
async def reset_password_confirm(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirm password reset with token."""
    # Verify the reset token
    email = verify_password_reset_token(reset_data.token)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Get user by email
    user = get_user_by_email(db, email)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    try:
        # Hash the new password
        hashed_password = get_password_hash(reset_data.new_password)
        
        # Update user password
        user_obj = db.query(UserModel).filter(UserModel.id == user.id).first()
        user_obj.password_hash = hashed_password
        user_obj.updated_at = datetime.utcnow()
        db.commit()
        
        # Invalidate all user sessions
        invalidate_user_sessions(db, user.id)
        
        return {"detail": "Password has been reset successfully. Please log in with your new password."}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )