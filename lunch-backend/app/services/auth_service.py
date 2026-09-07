from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.orm import AuthProvider, User, UserRole, UserStatus
from app.services.exceptions import (
    AccountRejectedError,
    EmailAlreadyRegisteredError,
    GoogleDomainNotAllowedError,
    GoogleSignInUnavailableError,
    IncorrectPasswordError,
    InternalStateError,
    InvalidCredentialsError,
    InvalidGoogleTokenError,
    NoPasswordSetError,
)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(func.lower(User.email) == email.lower()).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def _create_user(
    db: Session,
    name: str,
    email: str,
    password_hash: str | None,
    provider: AuthProvider,
    phone_number: str | None = None,
) -> User:

    user = User(
        name=name,
        email=email,
        password_hash=password_hash,
        auth_provider=provider,
        phone_number=phone_number,
        role=UserRole.employee,
        status=UserStatus.pending,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise EmailAlreadyRegisteredError(
            "This account is already registered.")
    db.refresh(user)
    return user


def register_user(db: Session, name: str, email: str, password: str, phone_number: str | None = None) -> User:
    if get_user_by_email(db, email):
        raise EmailAlreadyRegisteredError(
            "This account is already registered.")
    return _create_user(db, name, email, hash_password(password), AuthProvider.password, phone_number)


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Incorrect email or password.")
    if user.status == UserStatus.rejected:
        raise AccountRejectedError("This account has been rejected.")
    return user


def google_authenticate(db: Session, id_token_str: str) -> User:
    if not settings.GOOGLE_CLIENT_ID:
        raise GoogleSignInUnavailableError(
            "Google Sign-In is not configured on this server.")

    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    try:
        idinfo = google_id_token.verify_oauth2_token(
            id_token_str, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
    except Exception:
        raise InvalidGoogleTokenError("Invalid Google token.")

    email = idinfo.get("email", "")
    domain = email.split("@")[-1].lower()
    if (
        not idinfo.get("email_verified")
        or domain != settings.ALLOWED_EMAIL_DOMAIN.lower()
        or idinfo.get("hd", "").lower() != settings.ALLOWED_EMAIL_DOMAIN.lower()
    ):
        raise GoogleDomainNotAllowedError(
            f"Only @{settings.ALLOWED_EMAIL_DOMAIN} Google Workspace accounts are accepted.")

    user = get_user_by_email(db, email)
    if not user:
        try:
            user = _create_user(db, idinfo.get("name") or email.split(
                "@")[0], email, None, AuthProvider.google)
        except EmailAlreadyRegisteredError:
            # Two simultaneous first-time Google sign-ins for the same
            # email — the account now exists, just fetch it.
            user = get_user_by_email(db, email)
            if not user:
                raise InternalStateError(
                    "Could not complete sign-in. Please try again.")

    if user.status == UserStatus.rejected:
        raise AccountRejectedError("This account has been rejected.")
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not user.password_hash:
        raise NoPasswordSetError(
            "This account signs in with Google and has no password to change.")
    if not verify_password(current_password, user.password_hash):
        raise IncorrectPasswordError("Current password is incorrect.")
    user.password_hash = hash_password(new_password)
    db.commit()


def issue_token(user: User) -> dict:
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "role": user.role.value,
        "status": user.status.value,
    }
