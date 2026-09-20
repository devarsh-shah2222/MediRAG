from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Feedback, User
from app.schemas import FeedbackRequest

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_feedback(
    req: FeedbackRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> dict:
    feedback = Feedback(
        user_id=user.id if user else None,
        conversation_id=req.conversation_id,
        message_id=req.message_id,
        rating=req.rating,
        comment=req.comment,
    )
    db.add(feedback)
    db.commit()
    return {"id": feedback.id}
