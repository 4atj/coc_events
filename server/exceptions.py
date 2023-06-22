from __future__ import annotations

from sanic import text
from sanic.request import Request

from sanic import Blueprint

class CocEventsException(Exception):
    def __init__(self, msg: str, status: int = 400) -> None:
        self.msg = msg
        self.status = status
        super().__init__()

    def __str__(self) -> str:
        return f"msg: {self.msg} | status_code: {self.status}"


exceptions_bluteprint = Blueprint('exceptions')

@exceptions_bluteprint.exception(CocEventsException)
def coc_events_error(request: Request, exception: CocEventsException):
    return text(exception.msg, status = exception.status)

# disabled for debugging purposes for now
# TODO: add an option to enable debugging for both types of exceptions
"""
@app.exception(Exception)
def internal_error(request: Request, exception: Exception):
    return text("Internal Error" + str(exception), status = 400)
"""