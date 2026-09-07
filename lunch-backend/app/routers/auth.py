from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import schemas
from app.models.orm import User
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    return auth_service.register_user(db, payload.name, payload.email, payload.password)


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(db, payload.email, payload.password)
    return auth_service.issue_token(user)


@router.post("/google", response_model=schemas.TokenResponse)
def google_sign_in(payload: schemas.GoogleSignInRequest, db: Session = Depends(get_db)):
    user = auth_service.google_authenticate(db, payload.id_token)
    return auth_service.issue_token(user)


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password")
def change_password(payload: schemas.ChangePasswordRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    auth_service.change_password(
        db, current_user, payload.current_password, payload.new_password)
    return {"detail": "Password updated successfully."}
