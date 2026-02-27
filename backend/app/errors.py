"""
Error helpers for consistent API error payloads.
"""

from fastapi import HTTPException

STATUS_CODE_DEFAULTS: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_SERVER_ERROR",
}


def build_error_payload(
    code: str,
    message: str,
    details=None,
    request_id: str | None = None,
) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
        "request_id": request_id,
    }


def raise_api_error(
    status_code: int,
    code: str,
    message: str,
    details=None,
) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
            "details": details,
        },
    )
