from __future__ import annotations

import json
from typing import Protocol

from pydantic import BaseModel, Field

from app.core.errors import AppError, ErrorCode
from app.schemas.deep_research import Evidence, MajorEvent


class DeepResearchAnswer(BaseModel):
    conclusion: str = Field(min_length=1, max_length=8_000)


class StructuredProvider(Protocol):
    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
    ) -> BaseModel: ...


class DeepResearchAnswerer(Protocol):
    async def answer(
        self,
        question: str,
        evidence: list[Evidence],
        events: list[MajorEvent],
    ) -> str: ...


class StructuredDeepResearchAnswerer:
    """Evidence-only conclusion synthesis using the shared LLM provider port."""

    def __init__(self, provider: StructuredProvider) -> None:
        self.provider = provider

    async def answer(
        self,
        question: str,
        evidence: list[Evidence],
        events: list[MajorEvent],
    ) -> str:
        try:
            result = await self.provider.generate_structured(
                system_prompt=(
                    "Synthesize a conclusion only from the supplied evidence. "
                    "Do not invent prices, financial facts, news, or causes. "
                    "Return JSON."
                ),
                user_prompt=json.dumps(
                    {
                        "question": question,
                        "major_events": [
                            event.model_dump(mode="json") for event in events
                        ],
                        "evidence": [
                            item.model_dump(mode="json") for item in evidence
                        ],
                    },
                    ensure_ascii=False,
                ),
                schema=DeepResearchAnswer,
            )
            return DeepResearchAnswer.model_validate(result).conclusion
        except Exception as exc:
            raise AppError(
                ErrorCode.LLM_ERROR,
                "Deep research synthesis failed.",
                status_code=502,
                retryable=True,
            ) from exc
