"""Serialization helpers for storing strict research reports as snapshots."""

import json
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from app.schemas.research import EquityResearchReport


def serialize_model(model: BaseModel) -> dict[str, Any]:
    """Convert a Pydantic model into JSON-compatible database data."""

    value = model.model_dump(mode="json")
    if not isinstance(value, dict):
        raise TypeError("A persisted Pydantic model must serialize to an object.")
    return value


def serialize_research_report(report: EquityResearchReport) -> dict[str, Any]:
    """Persist the complete validated report, including score evidence."""

    return serialize_model(report)


def deserialize_research_report(
    payload: Mapping[str, Any],
) -> EquityResearchReport:
    """Rehydrate a report snapshot with the current strict schema."""

    return EquityResearchReport.model_validate_json(json.dumps(dict(payload)))
