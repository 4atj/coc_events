from __future__ import annotations

class CocEventsException(Exception):
    def __init__(self, msg: str) -> None:
        self.msg = msg
        super().__init__()

    def __str__(self) -> str:
        return self.msg