from __future__ import annotations

from pydantic import BaseModel


class IdentifyRequest(BaseModel):
    signals: dict
    visitorId: str | None = None
    accountId: str | None = None


class IdentifyResponse(BaseModel):
    visitorId: str
    isNewVisitor: bool
    serverReachable: bool
