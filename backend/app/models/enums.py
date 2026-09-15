"""Stable database status values."""

from enum import StrEnum


class ResearchTaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FilingType(StrEnum):
    TEN_K = "10-K"
    TEN_Q = "10-Q"
