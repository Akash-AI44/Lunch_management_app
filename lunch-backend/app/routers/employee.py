from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_active
from app.models import schemas
from app.models.orm import User
from app.services import employee_service

router = APIRouter(prefix="/employee", tags=["Employee"])


@router.get("/today", response_model=schemas.TodayStatusOut)
def get_today(db: Session = Depends(get_db), current_user: User = Depends(require_active)):
    return employee_service.get_today_status(db, current_user)


@router.patch("/today", response_model=schemas.TodayStatusOut)
def update_today(payload: schemas.ToggleLunchRequest, db: Session = Depends(get_db), current_user: User = Depends(require_active)):
    return employee_service.update_today_status(db, current_user, payload.is_having_lunch)


@router.get("/history", response_model=list[schemas.HistoryEntryOut])
def get_history(month: str = Query(..., examples=["2026-08"]), db: Session = Depends(get_db), current_user: User = Depends(require_active)):
    return employee_service.get_history(db, current_user, month)


@router.get("/summary", response_model=schemas.MonthlySummaryOut)
def get_summary(month: str = Query(..., examples=["2026-08"]), db: Session = Depends(get_db), current_user: User = Depends(require_active)):
    return employee_service.get_summary(db, current_user, month)


@router.post("/profile-picture", response_model=schemas.UserOut)
def upload_profile_picture(file: UploadFile, db: Session = Depends(get_db), current_user: User = Depends(require_active)):
    content = file.file.read()
    return employee_service.save_profile_picture(db, current_user, file.filename or "", file.content_type or "", content)
