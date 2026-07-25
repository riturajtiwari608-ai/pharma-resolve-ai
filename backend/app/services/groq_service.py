import json
import logging
from dataclasses import dataclass
from typing import Any

from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    Groq,
    RateLimitError,
)
from pydantic import ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.exceptions import (
    AIConfigurationError,
    AIModelUnavailableError,
    AIResponseValidationError,
    AIServiceError,
)
from app.prompts.complaint_extraction import (
    COMPLAINT_EXTRACTION_SYSTEM_PROMPT,
    build_complaint_extraction_user_prompt,
)
from app.schemas.ai_intake import (
    AIUsageInfo,
    ComplaintAnalysisResult,
)

logger = logging.getLogger(__name__)


@dataclass
class GroqAnalysisOutput:
    analysis: ComplaintAnalysisResult
    usage: AIUsageInfo


def _get_client() -> Groq:
    api_key_secret = settings.GROQ_API_KEY

    if api_key_secret is None:
        raise AIConfigurationError(
            "GROQ_API_KEY is missing from environment configuration."
        )

    api_key = api_key_secret.get_secret_value().strip()

    if not api_key:
        raise AIConfigurationError(
            "GROQ_API_KEY is missing from environment configuration."
        )

    return Groq(
        api_key=api_key,
        timeout=settings.GROQ_TIMEOUT_SECONDS,
    )


def _extract_json_object(content: str) -> dict[str, Any]:
    """
    Parse the model response as JSON.

    A limited fallback removes accidental markdown code fences without
    attempting to guess or repair arbitrary malformed output.
    """

    cleaned = content.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AIResponseValidationError(
            "Groq returned a response that was not valid JSON."
        ) from exc

    if not isinstance(parsed, dict):
        raise AIResponseValidationError("Groq response must be a JSON object.")

    return parsed
def _unwrap_extracted_values(
    parsed_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Normalize AI responses when the model wraps extraction fields like:

    {
        "customer_name": {
            "value": "Apollo Pharmacy",
            "confidence": 0.98,
            "source_text": "Apollo Pharmacy reported"
        }
    }

    into the flat format expected by ComplaintExtractionData:

    {
        "customer_name": "Apollo Pharmacy"
    }

    Evidence is preserved inside field_evidence whenever possible.
    """

    extraction = parsed_data.get("extraction")

    if not isinstance(extraction, dict):
        return parsed_data

    existing_evidence = parsed_data.get("field_evidence")

    if not isinstance(existing_evidence, dict):
        existing_evidence = {}

    normalized_extraction: dict[str, Any] = {}

    for field_name, field_value in extraction.items():
        if (
            isinstance(field_value, dict)
            and "value" in field_value
        ):
            normalized_extraction[field_name] = field_value.get(
                "value"
            )

            if field_name in {
                "complaint_source",
                "customer_name",
                "product_name",
                "product_strength_grade",
                "batch_lot_number",
                "affected_quantity",
                "manufacturing_date",
                "expiry_date",
            }:
                existing_evidence[field_name] = {
                    "value": field_value.get("value"),
                    "confidence": field_value.get(
                        "confidence",
                        0,
                    ),
                    "source_text": field_value.get(
                        "source_text"
                    ),
                }
        else:
            normalized_extraction[field_name] = field_value

    parsed_data["extraction"] = normalized_extraction
    parsed_data["field_evidence"] = existing_evidence

    return parsed_data


def _is_model_unavailable_error(exc: APIStatusError) -> bool:
    response_text = str(exc).lower()

    unavailable_terms = (
        "model_decommissioned",
        "model_not_found",
        "does not exist",
        "not found",
        "unsupported model",
        "invalid model",
    )

    return any(term in response_text for term in unavailable_terms)


@retry(
    retry=retry_if_exception_type(
        (
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
        )
    ),
    wait=wait_exponential(
        multiplier=1,
        min=1,
        max=8,
    ),
    stop=stop_after_attempt(3),
    reraise=True,
)
def _request_analysis(
    client: Groq,
    model: str,
    complaint_text: str,
):
    return client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": COMPLAINT_EXTRACTION_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": build_complaint_extraction_user_prompt(complaint_text),
            },
        ],
        temperature=settings.GROQ_TEMPERATURE,
        max_completion_tokens=settings.GROQ_MAX_COMPLETION_TOKENS,
        response_format={
            "type": "json_object",
        },
    )


def _call_model(
    client: Groq,
    model: str,
    complaint_text: str,
):
    try:
        return _request_analysis(
            client=client,
            model=model,
            complaint_text=complaint_text,
        )
    except APIStatusError as exc:
        if _is_model_unavailable_error(exc):
            raise AIModelUnavailableError(
                f"Groq model '{model}' is unavailable."
            ) from exc

        raise AIServiceError(f"Groq returned API status {exc.status_code}.") from exc
    except RateLimitError as exc:
        raise AIServiceError(
            "Groq rate limit was reached. Please retry shortly."
        ) from exc
    except APITimeoutError as exc:
        raise AIServiceError("Groq request timed out.") from exc
    except APIConnectionError as exc:
        raise AIServiceError("Could not connect to Groq.") from exc


def analyze_complaint_text(
    complaint_text: str,
) -> GroqAnalysisOutput:
    client = _get_client()

    requested_model = settings.GROQ_MODEL
    used_model = requested_model
    fallback_used = False

    try:
        completion = _call_model(
            client=client,
            model=requested_model,
            complaint_text=complaint_text,
        )
    except AIModelUnavailableError:
        fallback_model = settings.GROQ_FALLBACK_MODEL

        if not fallback_model or fallback_model == requested_model:
            raise

        logger.warning(
            "Primary model %s unavailable. Using fallback model %s.",
            requested_model,
            fallback_model,
        )

        used_model = fallback_model
        fallback_used = True

        completion = _call_model(
            client=client,
            model=fallback_model,
            complaint_text=complaint_text,
        )

    content = completion.choices[0].message.content

    if not content:
        raise AIResponseValidationError("Groq returned an empty response.")

    parsed_data = _extract_json_object(content)
    parsed_data = _unwrap_extracted_values(
    parsed_data
    )

    try:
        analysis = ComplaintAnalysisResult.model_validate(parsed_data)
    except ValidationError as exc:
        logger.error(
            "AI response schema validation failed: %s",
            exc,
        )

        raise AIResponseValidationError(
            "Groq response did not match the complaint schema."
        ) from exc

    usage = getattr(completion, "usage", None)

    usage_info = AIUsageInfo(
        requested_model=requested_model,
        used_model=used_model,
        prompt_tokens=(getattr(usage, "prompt_tokens", None) if usage else None),
        completion_tokens=(
            getattr(usage, "completion_tokens", None) if usage else None
        ),
        total_tokens=(getattr(usage, "total_tokens", None) if usage else None),
        fallback_used=fallback_used,
    )

    return GroqAnalysisOutput(
        analysis=analysis,
        usage=usage_info,
    )
