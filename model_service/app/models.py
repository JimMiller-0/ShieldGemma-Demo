from pydantic import BaseModel, Field


class SafetyPrompt(BaseModel):
    category: str = Field(..., description="Safety policy category name.")
    text: str = Field(..., max_length=32768, description="Fully constructed prompt for this category.")


class SafetyRequest(BaseModel):
    model_id: str = Field(..., description="ShieldGemma model identifier.")
    prompts: list[SafetyPrompt] = Field(..., description="Category prompts to evaluate.")
    max_new_tokens: int = Field(default=128, le=1024, description="Max new tokens (unused in scoring mode).")


class SafetyCategoryResult(BaseModel):
    category: str = Field(..., description="Safety policy category name.")
    yes_prob: float = Field(..., description="Probability of violation (0.0 to 1.0).")
    no_prob: float = Field(..., description="Probability of safe (0.0 to 1.0).")
    raw_text: str = Field(..., description="'Yes' or 'No' based on threshold.")


class SafetyResponse(BaseModel):
    model_id: str = Field(..., description="Model that produced these results.")
    results: list[SafetyCategoryResult] = Field(..., description="Per-category safety results.")
    inference_time_ms: float = Field(..., description="Batch inference time in milliseconds.")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status.")
    model_loaded: str | None = Field(None, description="Currently loaded model identifier.")
    device: str = Field(..., description="Compute device in use.")
