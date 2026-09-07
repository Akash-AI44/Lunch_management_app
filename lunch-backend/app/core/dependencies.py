from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.orm import User, UserRole, UserStatus
from app.services.auth_service import get_user_by_id

# HTTPBearer (not OAuth2PasswordBearer) because this API's /auth/login
# takes JSON, not an OAuth2 form-post — HTTPBearer gives Swagger UI a
# plain "paste your token" field instead of a username/password form
# that would try (and fail) to log in against a form-encoded endpoint.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    error = HTTPException(status_code=401, detail="Could not validate credentials", headers={
                          "WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise error
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise error
    user = get_user_by_id(db, int(payload.get("sub", 0)))
    if user is None:
        raise error
    return user


def require_active(current_user: User = Depends(get_current_user)) -> User:
    if current_user.status != UserStatus.active:
        raise HTTPException(
            status_code=403, detail="Your account is awaiting activation by a superadmin.")
    return current_user


def require_superadmin(current_user: User = Depends(require_active)) -> User:
    if current_user.role != UserRole.superadmin:
        raise HTTPException(
            status_code=403, detail="Superadmin access required.")
    return current_user
