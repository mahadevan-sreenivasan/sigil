from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class IdentifyRequest(BaseModel):
    signals: dict
    visitorId: str | None = None
    accountId: str | None = None


class SimilarVisitor(BaseModel):
    visitorId: str
    similarityScore: float
    lastSeenAt: str | None = None
    matchingSignals: list[str] = []
    mismatchedSignals: list[str] = []
    accountIds: list[str] | None = None


class AccountHistory(BaseModel):
    knownVisitorCount: int = 0
    isKnownVisitorForAccount: bool = False


class IdentifyResponse(BaseModel):
    visitorId: str
    fingerprintId: str
    isNewVisitor: bool
    signalValidation: Literal["new", "match", "mismatch"]
    serverReachable: bool
    similarVisitors: list[SimilarVisitor] = []
    accountHistory: AccountHistory | None = None


class CreateApiKeyRequest(BaseModel):
    allowedOrigins: list[str] = []


class CreateApiKeyResponse(BaseModel):
    publishableKey: str
    secretKey: str
