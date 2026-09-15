from __future__ import annotations

import re
from dataclasses import dataclass

from app.providers.sec.base import FilingMetadata


@dataclass(frozen=True, slots=True)
class FilingChunk:
    chunk_id: str
    metadata: FilingMetadata
    section: str
    text: str


def clean_filing_text(text: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def chunk_filing(
    filing: FilingMetadata,
    text: str,
    *,
    section: str = "filing",
    chunk_size: int = 1_200,
    overlap: int = 150,
) -> list[FilingChunk]:
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")
    cleaned = clean_filing_text(text)
    chunks: list[FilingChunk] = []
    step = chunk_size - overlap
    for index, start in enumerate(range(0, len(cleaned), step)):
        excerpt = cleaned[start : start + chunk_size]
        if excerpt:
            chunks.append(
                FilingChunk(
                    chunk_id=f"{filing.accession_number}:{section}:{index}",
                    metadata=filing,
                    section=section,
                    text=excerpt,
                )
            )
    return chunks
