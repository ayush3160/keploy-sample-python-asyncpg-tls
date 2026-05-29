from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class HttpError(Exception):
    def __init__(self, code: int, message: str, *, retryable: bool = False, reason: str = ""):
        self.code = code
        self.message = message
        self.retryable = retryable
        self.reason = reason


def _envelope(code: int, message: str, *, retryable: bool = False, reason: str = "") -> dict:
    return {
        "code": code,
        "context": {"errors": []},
        "message": message,
        "retryable": retryable,
        "reason": reason,
    }


async def http_error_handler(_: Request, exc: HttpError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.code,
        content=_envelope(exc.code, exc.message, retryable=exc.retryable, reason=exc.reason),
    )


async def integrity_error_handler(_: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(status_code=409, content=_envelope(409, str(exc)))
