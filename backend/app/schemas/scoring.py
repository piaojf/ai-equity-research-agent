from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class ScoreComponent(BaseModel):
    metric: str = Field(min_length=1)
    raw_value: float | None
    normalized_score: float | None = Field(default=None, ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    contribution: float = Field(ge=0, le=100)
    source: str = Field(min_length=1)
    source_url: HttpUrl | None = None

    @model_validator(mode="after")
    def validate_contribution(self) -> "ScoreComponent":
        if self.normalized_score is not None:
            expected = self.normalized_score * self.weight
            if abs(self.contribution - expected) > 1e-6:
                raise ValueError(
                    "contribution must equal normalized_score multiplied by weight"
                )
        return self


class ScoreBreakdown(BaseModel):
    score_name: str = Field(min_length=1)
    final_score: int = Field(ge=0, le=100)
    components: list[ScoreComponent]
    methodology_version: str = Field(min_length=1)
    missing_metrics: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]

    @model_validator(mode="after")
    def validate_components(self) -> "ScoreBreakdown":
        if self.components:
            total_weight = sum(component.weight for component in self.components)
            if abs(total_weight - 1.0) > 1e-6:
                raise ValueError("score component weights must sum to one")
            total_contribution = sum(
                component.contribution for component in self.components
            )
            if abs(total_contribution - self.final_score) > 1.0:
                raise ValueError("score contributions must explain final_score")
        return self
