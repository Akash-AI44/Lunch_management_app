"""Routers layer for /admin. Thin: parse the request, call the service
layer, return the result."""
from datetime import date as date_cls

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_superadmin
from app.models import schemas
from app.models.orm import User
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/pending", response_model=list[schemas.UserOut])
def list_pending(db: Session = Depends(get_db), current_user: User = Depends(require_superadmin)):
    return admin_service.list_pending_users(db)


@router.post("/activate/{user_id}", response_model=schemas.ActivateRejectResponse)
def activate_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_superadmin)):
    user = admin_service.activate_user(db, user_id)
    return {"id": user.id, "status": user.status.value}


@router.post("/reject/{user_id}", response_model=schemas.ActivateRejectResponse)
def reject_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_superadmin)):
    user = admin_service.reject_user(db, user_id)
    return {"id": user.id, "status": user.status.value}


@router.get("/daily", response_model=schemas.DailyCountOut)
def daily_count(on: date_cls | None = Query(None, description="Defaults to today"), db: Session = Depends(get_db), current_user: User = Depends(require_superadmin)):
    return admin_service.get_daily_count(db, on)


@router.get("/monthly", response_model=schemas.MonthlyTotalsOut)
def monthly_totals(month: str = Query(..., examples=["2026-08"]), db: Session = Depends(get_db), current_user: User = Depends(require_superadmin)):
    return admin_service.get_monthly_totals(db, month)


@router.get("/history", response_model=schemas.MonthlyHistoryOut)
def monthly_history(month: str = Query(..., examples=["2026-08"]), db: Session = Depends(get_db), current_user: User = Depends(require_superadmin)):
    return admin_service.get_monthly_history(db, month)


@router.get("/history/day", response_model=schemas.DayDrilldownOut)
def day_drilldown(on: date_cls, db: Session = Depends(get_db), current_user: User = Depends(require_superadmin)):
    return admin_service.get_day_drilldown(db, on)


@router.get("/export")
def export_daily_csv(on: date_cls | None = Query(None, description="Defaults to today"), db: Session = Depends(get_db), current_user: User = Depends(require_superadmin)):
    filename, csv_text = admin_service.export_daily_csv(db, on)
    return StreamingResponse(iter([csv_text]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/settings", response_model=schemas.CutoffSettingsOut)
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(require_superadmin)):
    return admin_service.get_cutoff_settings(db)


@router.patch("/settings", response_model=schemas.CutoffSettingsOut)
def update_settings(payload: schemas.UpdateCutoffRequest, db: Session = Depends(get_db), current_user: User = Depends(require_superadmin)):
    return admin_service.update_cutoff_settings(db, payload.cutoff_hour, payload.cutoff_minute)
