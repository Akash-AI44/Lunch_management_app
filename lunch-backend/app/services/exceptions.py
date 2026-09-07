class ServiceError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class EmailAlreadyRegisteredError(ServiceError):
    status_code = 409


class InvalidCredentialsError(ServiceError):
    status_code = 401


class AccountRejectedError(ServiceError):
    status_code = 403


class AccountNotActiveError(ServiceError):
    status_code = 403


class UserNotFoundError(ServiceError):
    status_code = 404


class UserNotPendingError(ServiceError):
    status_code = 400


class NoLunchFeatureError(ServiceError):
    status_code = 400


class CutoffPassedError(ServiceError):
    status_code = 403


class InvalidMonthFormatError(ServiceError):
    status_code = 422


class InvalidImageTypeError(ServiceError):
    status_code = 415


class GoogleSignInUnavailableError(ServiceError):
    status_code = 503


class InvalidGoogleTokenError(ServiceError):
    status_code = 401


class GoogleDomainNotAllowedError(ServiceError):
    status_code = 403


class NoPasswordSetError(ServiceError):
    status_code = 400


class IncorrectPasswordError(ServiceError):
    status_code = 400


class InternalStateError(ServiceError):
    status_code = 500
