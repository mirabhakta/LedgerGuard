from pydantic import BaseModel, Field


class PolicyConfig(BaseModel):
    goal_misalignment_block_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    duplicate_block_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    counterparty_review_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    missing_context_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    anomaly_review_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    minimum_confidence_threshold: float = Field(default=0.60, ge=0.0, le=1.0)
