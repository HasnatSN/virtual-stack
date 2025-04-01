from fastapi import HTTPException, status


class VirtualStackException(Exception):
    """Base exception for VirtualStack errors."""


class DatabaseError(VirtualStackException):
    """Exception raised for database related errors."""


class NotFoundError(VirtualStackException):
    """Exception raised when a resource is not found."""


class AuthenticationError(VirtualStackException):
    """Exception raised for authentication errors."""


class AuthorizationError(VirtualStackException):
    """Exception raised for authorization errors."""


class ValidationError(VirtualStackException):
    """Exception raised for validation errors."""


# HTTP Exception factories
def http_not_found_error(detail: str = "Resource not found") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=detail,
    )


def http_authentication_error(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def http_authorization_error(detail: str = "Not enough permissions") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


def http_validation_error(detail: str = "Validation error") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=detail,
    )


def http_bad_request_error(detail: str = "Bad request") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )
