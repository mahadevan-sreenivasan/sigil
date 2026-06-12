from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class IdentifyRequest(BaseModel):
    signals: dict
    visitorId: str | None = None
    accountId: str | None = None


class IdentifyResponse(BaseModel):
    visitorId: str
    fingerprintId: str
    isNewVisitor: bool
    signalValidation: Literal["new", "match", "mismatch"]
    serverReachable: bool
