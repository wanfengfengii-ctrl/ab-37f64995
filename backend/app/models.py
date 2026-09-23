"""Pydantic models for the beam pulse reconciliation API."""
from __future__ import annotations

import re
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

_EVENT_CODE_RE = re.compile(r"^[A-Z0-9]{1,8}$")


class Event(BaseModel):
    """A single recorded pulse: integer timestamp and event code."""

    time: int = Field(..., ge=0, le=10**12)
    code: str

    @field_validator("code")
    @classmethod
    def _validate_code(cls, v: str) -> str:
        if not _EVENT_CODE_RE.match(v):
            raise ValueError("event code must be 1-8 uppercase letters or digits")
        return v


class AdjudicateRequest(BaseModel):
    """Request payload for the reconciliation verdict."""

    stream_a: List[Event] = Field(..., alias="streamA", min_length=2, max_length=80)
    stream_b: List[Event] = Field(..., alias="streamB", min_length=2, max_length=80)
    min_offset: int = Field(..., alias="minOffset")
    max_offset: int = Field(..., alias="maxOffset")
    jump: int = Field(..., ge=0)
    min_hits: int = Field(..., alias="minHits", ge=1, le=80)

    model_config = {"populate_by_name": True}

    @field_validator("stream_a", "stream_b")
    @classmethod
    def _strict_increasing(cls, events: List[Event]) -> List[Event]:
        for prev, cur in zip(events, events[1:]):
            if cur.time <= prev.time:
                raise ValueError("timestamps must be strictly increasing")
        return events

    @field_validator("max_offset")
    @classmethod
    def _range_consistent(cls, v: int, info) -> int:
        mn = info.data.get("min_offset")
        if mn is not None and v < mn:
            raise ValueError("maxOffset must be >= minOffset")
        return v


class MatchedPair(BaseModel):
    index_a: int = Field(..., alias="indexA")
    index_b: int = Field(..., alias="indexB")
    time_a: int = Field(..., alias="timeA")
    time_b: int = Field(..., alias="timeB")
    code: str
    offset: int
    offset_before: int = Field(..., alias="offsetBefore")
    offset_after: int = Field(..., alias="offsetAfter")
    jump_applied_before: bool = Field(..., alias="jumpAppliedBefore")

    model_config = {"populate_by_name": True}


class Solution(BaseModel):
    initial_offset: int = Field(..., alias="initialOffset")
    jump_direction: Literal["none", "plus", "minus"] = Field(
        ..., alias="jumpDirection"
    )
    jump_index_a: Optional[int] = Field(None, alias="jumpIndexA")
    jump_index_b: Optional[int] = Field(None, alias="jumpIndexB")
    matches_before_jump: int = Field(..., alias="matchesBeforeJump")
    pairs: List[MatchedPair]
    pair_indices: List[List[int]] = Field(..., alias="pairIndices")

    model_config = {"populate_by_name": True}


class AdjudicateResponse(BaseModel):
    feasible: bool
    match_count: int = Field(..., alias="matchCount")
    min_hits: int = Field(..., alias="minHits")
    uniqueness: Optional[Literal["unique", "ambiguous"]] = None
    solution: Optional[Solution] = None
    witness: Optional[Solution] = None
    reason: Optional[str] = None

    model_config = {"populate_by_name": True}
