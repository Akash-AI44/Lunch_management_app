from datetime import date

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
    return employee_service.update_today_status(db, current_user, payload.is_having_lunch, payload.reason)


@router.post("/leave", response_model=schemas.LeaveResponse)
def apply_leave(payload: schemas.LeaveRequest, db: Session = Depends(get_db), current_user: User = Depends(require_active)):
    updated_days = employee_service.apply_leave(
        db, current_user, payload.start_date, payload.end_date, payload.reason)
    return {"updated_days": updated_days}


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


@router.get("/leave", response_model=list[schemas.LeaveDayOut])
def get_upcoming_leave(db: Session = Depends(get_db), current_user: User = Depends(require_active)):
    return employee_service.get_upcoming_leave(db, current_user)


@router.delete("/leave/{target_date}", response_model=schemas.LeaveDayOut)
def cancel_leave_day(target_date: date, db: Session = Depends(get_db), current_user: User = Depends(require_active)):
    return employee_service.cancel_leave_day(db, current_user, target_date)
