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


class Velocity(BaseModel):
    visitorRequestsLast10Min: int
    accountDistinctVisitorsLast1Hr: int | None = None
    ipDistinctAccountsLast1Hr: int | None = None


class Geolocation(BaseModel):
    ip: str
    country: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class PreviousLocation(BaseModel):
    country: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class ImpossibleTravel(BaseModel):
    detected: bool = False
    previousLocation: PreviousLocation | None = None
    previousSeenAt: str | None = None
    distanceKm: float | None = None


class IdentifyResponse(BaseModel):
    visitorId: str
    fingerprintId: str
    isNewVisitor: bool
    signalValidation: Literal["new", "match", "mismatch"]
    serverReachable: bool
    geolocation: Geolocation | None = None
    impossibleTravel: ImpossibleTravel | None = None
    similarVisitors: list[SimilarVisitor] = []
    accountHistory: AccountHistory | None = None
    velocity: Velocity | None = None


class CreateApiKeyRequest(BaseModel):
    allowedOrigins: list[str] = []


class CreateApiKeyResponse(BaseModel):
    publishableKey: str
    secretKey: str
