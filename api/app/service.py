import time

from fastapi import HTTPException
import httpx
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from api.app import crud
from api.app.config import settings
from api.app.schemas import SafetyAnalysisRequest, SafetyAnalysisResponse, SafetyCategory


PREDEFINED_POLICIES = {
    "Dangerous Content": (
        '"No Dangerous Content": The prompt shall not contain or seek generation of content that '
        "harming oneself and/or others (e.g., accessing or building firearms and explosive devices, "
        "promotion of terrorism, instructions for suicide)."
    ),
    "Harassment": (
        '"No Harassment": The prompt shall not contain or seek generation of content that is malicious, '
        "intimidating, bullying, or abusive content targeting another individual (e.g., physical threats, "
        "denial of tragic events, disparaging victims of violence)."
    ),
    "Hate Speech": (
        '"No Hate Speech": The prompt shall not contain or seek generation of content that targeting '
        "identity and/or protected attributes (e.g., racial slurs, promotion of discrimination, calls "
        "to violence against protected groups) or dehumanizing/belittling/vilifying on the bases of race, "
        "ethnicity, religion, disability, age, nationality, veteran status, sexual orientation, gender, "
        "gender identity, caste, or any other protected status. We do allow content that includes a "
        "reference to a protected individual or group in a positive manner."
    ),
    "Sexually Explicit Information": (
        '"No Sexually Explicit Information": The prompt shall not contain or seek generation of content '
        "that contains references to sexual acts or other lewd content (e.g., sexually graphic descriptions, "
        "content aimed at causing arousal). Medical or scientific terms related to human anatomy or sex "
        "education are permitted."
    ),
}

PREDEFINED_POLICY_KEY_MAP = {
    "dangerous_content": "Dangerous Content",
    "harassment": "Harassment",
    "hate_speech": "Hate Speech",
    "sexually_explicit": "Sexually Explicit Information",
}

MAX_PROMPT_CHARS = 8192


def construct_prompt(text_input: str, policy: str) -> str:
    preamble = (
        "You are a policy expert trying to help determine whether a user "
        "prompt is in violation of the defined safety policies."
    )
    user_section = f"<start_of_turn>\nHuman User Prompt: {text_input}\n<end_of_turn>"
    guideline_section = f"Our safety principle is defined in the below:\n\n* {policy}"
    epilogue = (
        "===\n\nDoes the human user prompt violate the above principle? "
        "Your answer must start with 'Yes' or 'No'. And then walk through "
        "step by step to be sure we answer correctly."
    )
    return f"{preamble}\n\n{user_section}\n\n{guideline_section}\n\n{epilogue}"


async def analyze_safety(
    request: SafetyAnalysisRequest,
    db: AsyncSession,
) -> SafetyAnalysisResponse:
    start_time = time.time()

    # 1. Determine policies to evaluate
    all_policies: dict[str, str] = {}
    predefined_config = {k: True for k in PREDEFINED_POLICY_KEY_MAP}
    policy_name: str | None = None

    if request.policy_id:
        custom_policy = await crud.get_safety_policy(db, request.policy_id)
        if custom_policy:
            policy_name = custom_policy.name
            if custom_policy.predefined_policy_config:
                predefined_config = custom_policy.predefined_policy_config
            all_policies[f"Policy Violation: {custom_policy.name}"] = custom_policy.policy_content

    for config_key, predefined_key in PREDEFINED_POLICY_KEY_MAP.items():
        if predefined_config.get(config_key, True):
            all_policies[predefined_key] = PREDEFINED_POLICIES[predefined_key]

    # 2. Build prompts
    safety_prompts = []
    for category, policy_text in all_policies.items():
        constructed = construct_prompt(request.text_input, policy_text)
        if len(constructed) > MAX_PROMPT_CHARS:
            raise ValueError(
                f"Prompt for '{category}' is {len(constructed)} chars, "
                f"exceeding the {MAX_PROMPT_CHARS}-char limit. Shorten your input."
            )
        safety_prompts.append({"category": category, "text": constructed})

    # 3. Call model service
    model_url = f"{settings.model_service_url}/v1/inference/safety"
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(model_url, json={
                "model_id": request.model_id,
                "prompts": safety_prompts,
            })
            resp.raise_for_status()
            model_response = resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                raise HTTPException(
                    status_code=503,
                    detail="Model is still initializing in the background. Please wait a moment and try again.",
                )
            raise

    # 4. Process response
    safety_categories: list[SafetyCategory] = []
    max_score = 0.0
    raw_outputs = []

    for r in model_response["results"]:
        score = r["yes_prob"]
        max_score = max(max_score, score)
        safety_categories.append(SafetyCategory(category=r["category"], score=score))
        raw_outputs.append(f"Category: {r['category']}\nScore: {score}\nRaw: {r['raw_text']}")

    is_safe = max_score < 0.5
    inference_time = time.time() - start_time

    # 5. Log analysis
    try:
        await crud.create_analysis_log(
            db=db,
            text_input=request.text_input,
            policy_id=request.policy_id,
            policy_name=policy_name,
            is_safe=is_safe,
            safety_categories=[{"category": c.category, "score": c.score} for c in safety_categories],
            model_used=request.model_id,
            max_score=max_score,
            inference_time_seconds=inference_time,
        )
    except Exception as e:
        logger.warning("Failed to log analysis result: {}", e)

    return SafetyAnalysisResponse(
        model_used=request.model_id,
        is_safe=is_safe,
        safety_categories=safety_categories,
        raw_output="\n\n".join(raw_outputs),
        inference_time_seconds=round(inference_time, 3),
        policy_name=policy_name,
    )
