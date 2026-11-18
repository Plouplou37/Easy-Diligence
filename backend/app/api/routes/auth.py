import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.email import email_service
from app.core.exceptions import TooManyRequestsError
from app.core.login_throttle import login_throttle
from app.core.security import (
    create_password_reset_token,
    create_tokens,
    read_password_reset_token,
    reset_token_matches,
    verify_token,
)
from app.models.user import User as UserModel
from app.schemas.user import (
    PasswordChange,
    PasswordReset,
    PasswordResetConfirm,
    RefreshRequest,
    Token,
    User,
    UserRegister,
    UserUpdate,
)
from app.services.auth import (
    authenticate_user,
    change_password,
    create_user,
    create_user_session,
    get_user_by_email,
    invalidate_user_sessions,
    rotate_user_session,
    set_password,
    update_user,
    validate_refresh_token,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _client_address(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
def register(user_register: UserRegister, db: Session = Depends(get_db)):
    """Register a new account. It is always an analyst: the schema has no role
    field and refuses one. Admins are made with `python -m app.cli create-admin`."""
    return create_user(db, user_register, password=user_register.password)


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login and receive access and refresh tokens."""
    email = form_data.username  # the username field carries the email
    address = _client_address(request)

    wait = login_throttle.retry_after(email, address)
    if wait:
        raise TooManyRequestsError("Too many failed login attempts. Try again later.", wait)

    user = authenticate_user(db, email, form_data.password)
    if not user:
        login_throttle.record_failure(email, address)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    login_throttle.record_success(email)

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    tokens = create_tokens(user.id, user.email, user.role)
    create_user_session(
        db, user.id, tokens["access_token"], tokens["refresh_token"],
        address, request.headers.get("User-Agent"),
    )
    return tokens


@router.post("/refresh", response_model=Token)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a refresh token (sent in the body) for a new pair of tokens."""
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not verify_token(body.refresh_token, token_type="refresh"):
        raise invalid

    user = validate_refresh_token(db, body.refresh_token)
    if not user or not user.is_active:
        raise invalid

    tokens = create_tokens(user.id, user.email, user.role)
    if not rotate_user_session(db, body.refresh_token,
                               tokens["access_token"], tokens["refresh_token"]):
        raise invalid
    return tokens


@router.get("/me", response_model=User)
def read_current_user(current_user: UserModel = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.put("/profile", response_model=User)
def update_profile(
    user_update: UserUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's profile."""
    return update_user(db, current_user.id, user_update.model_dump(exclude_unset=True))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    """Logout: invalidate every session of the current user."""
    invalidate_user_sessions(db, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_user_password(
    password_change: PasswordChange,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the current user's password; every session is closed after it."""
    if not change_password(db, current_user.id,
                           password_change.current_password, password_change.new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Current password is incorrect")

    invalidate_user_sessions(db, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reset-password", status_code=status.HTTP_202_ACCEPTED)
async def reset_password_request(password_reset: PasswordReset, db: Session = Depends(get_db)):
    """Request a password reset link. The answer is the same whether or not the
    address exists, so it cannot be used to find accounts."""
    user = get_user_by_email(db, password_reset.email)

    if user and user.is_active:
        reset_token = create_password_reset_token(user.email, user.password_hash)
        email_sent = await email_service.send_password_reset_email(
            to_email=user.email,
            reset_token=reset_token,
            user_name=user.full_name or "",
        )
        if not email_sent:
            logger.error("Password reset email could not be sent (user id %s)", user.id)

    return {"detail": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password-confirm", status_code=status.HTTP_200_OK)
def reset_password_confirm(reset_data: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Set a new password with a reset token. A token works once: it is tied to
    the password it was issued for."""
    invalid = HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid or expired reset token")

    token = read_password_reset_token(reset_data.token)
    if not token:
        raise invalid

    user = get_user_by_email(db, token["email"])
    if not user or not user.is_active or not reset_token_matches(token["fp"], user.password_hash):
        raise invalid

    set_password(db, user, reset_data.new_password)
    invalidate_user_sessions(db, user.id)

    return {"detail": "Password has been reset successfully. Please log in with your new password."}
