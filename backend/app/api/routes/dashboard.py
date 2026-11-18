"""Dashboard: every session of the user, with the state of each of its DD types."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.services.dashboard import dashboard

router = APIRouter()


@router.get("/sessions")
def dashboard_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Sessions visible to the user, each with the state of its DD types."""
    return dashboard(db, current_user)
