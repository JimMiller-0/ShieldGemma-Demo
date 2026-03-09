from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


# --- Predefined Policy Config ---

class PredefinedPolicyConfig(BaseModel):
    dangerous_content: bool = Field(True, description="Include 'Dangerous Content' predefined policy")
    harassment: bool = Field(True, description="Include 'Harassment' predefined policy")
    hate_speech: bool = Field(True, description="Include 'Hate Speech' predefined policy")
    sexually_explicit: bool = Field(True, description="Include 'Sexually Explicit Information' predefined policy")


# --- Safety Policy ---

class SafetyPolicyCreate(BaseModel):
    name: str = Field(..., max_length=255, description="Policy name")
    description: Optional[str] = Field(None, description="Description of the policy")
    policy_content: str = Field(..., description="The policy content defining moderation rules")
    is_default: bool = Field(False, description="Whether this is the default policy")
    predefined_policy_config: PredefinedPolicyConfig = Field(
        default_factory=PredefinedPolicyConfig,
        description="Toggle predefined safety categories",
    )


class SafetyPolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    policy_content: Optional[str] = None
    is_default: Optional[bool] = None
    predefined_policy_config: Optional[PredefinedPolicyConfig] = None


class SafetyPolicyResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    policy_content: str
    is_default: bool
    predefined_policy_config: dict
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class SafetyPolicyListResponse(BaseModel):
    policies: list[SafetyPolicyResponse]
    total: int


# --- Safety Analysis ---

class SafetyAnalysisRequest(BaseModel):
    text_input: str = Field(..., max_length=8000, description="Text to analyze")
    model_id: str = Field(default="google/shieldgemma-2b", description="Model to use")
    policy_id: Optional[UUID] = Field(None, description="Policy ID to use; defaults to default policy")


class SafetyCategory(BaseModel):
    category: str
    score: float


class SafetyAnalysisResponse(BaseModel):
    model_used: str
    is_safe: bool
    safety_categories: list[SafetyCategory]
    raw_output: str
    inference_time_seconds: float
    policy_name: Optional[str] = None


# --- Analysis Logs ---

class AnalysisLogResponse(BaseModel):
    id: UUID
    text_input: str
    policy_id: Optional[UUID]
    policy_name: Optional[str]
    is_safe: bool
    safety_categories: list[dict]
    model_used: str
    max_score: float
    inference_time_seconds: float
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisLogListResponse(BaseModel):
    logs: list[AnalysisLogResponse]
    total: int
