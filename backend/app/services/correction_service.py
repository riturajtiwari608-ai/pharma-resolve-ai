import json
import logging
from datetime import date
from typing import Any

from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    Groq,
    RateLimitError,
)
from pydantic import ValidationError

from app.core.config import settings
from app.core.exceptions import (
    AIResponseValidationError,
    AIServiceError,
)
from app.prompts.complaint_correction import (
    COMPLAINT_CORRECTION_SYSTEM_PROMPT,
    build_complaint_correction_prompt,
)
from app.schemas.copilot import ComplaintCorrectionResult


logger = logging.getLogger(__name__)


ALLOWED_UPDATE_FIELDS = {
    "complaint_source",
    "customer_name",
    "product_name",
    "product_strength_grade",
    "batch_lot_number",
    "affected_quantity",
    "affected_quantity_unit",
    "manufacturing_date",
    "expiry_date",
    "originating_site_block",
    "impacted_non_product_material",
    "complaint_category",
    "structured_defect_summary",
    "suggested_severity",
    "suggested_next_action",
    "initial_risk_assessment",
}


def _remove_code_fences(content: str) -> str:
    cleaned = content.strip()

    if not cleaned.startswith("```"):
        return cleaned

    lines = cleaned.splitlines()

    if lines and lines[0].startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    cleaned = "\n".join(lines).strip()

    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()

    return cleaned


def _parse_correction_json(
    content: str,
) -> dict[str, Any]:
    cleaned = _remove_code_fences(content)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AIResponseValidationError(
            "Correction model returned invalid JSON."
        ) from exc

    if not isinstance(parsed, dict):
        raise AIResponseValidationError(
            "Correction response must be a JSON object."
        )

    return parsed


def _normalize_field_updates(
    updates: dict[str, Any],
) -> dict[str, Any]:
    """
    Keep only safe complaint fields and normalize wrapped values.
    """

    normalized: dict[str, Any] = {}

    for field_name, field_value in updates.items():
        if field_name not in ALLOWED_UPDATE_FIELDS:
            continue

        if (
            isinstance(field_value, dict)
            and "value" in field_value
        ):
            field_value = field_value.get("value")

        if field_name == "affected_quantity":
            if field_value is None:
                normalized[field_name] = None
                continue

            try:
                field_value = float(field_value)
            except (TypeError, ValueError):
                continue

        if field_name in {
            "manufacturing_date",
            "expiry_date",
        }:
            if field_value is None:
                normalized[field_name] = None
                continue

            try:
                field_value = date.fromisoformat(
                    str(field_value)
                ).isoformat()
            except ValueError:
                continue

        if field_name == "suggested_severity":
            allowed_severities = {
                "critical",
                "major",
                "minor",
                "unclassified",
            }

            normalized_severity = str(field_value).lower()

            if normalized_severity not in allowed_severities:
                continue

            field_value = normalized_severity

        if isinstance(field_value, str):
            field_value = field_value.strip()

            if not field_value:
                field_value = None

        normalized[field_name] = field_value

    return normalized


def extract_complaint_corrections(
    user_message: str,
    existing_complaint: dict[str, Any],
) -> ComplaintCorrectionResult:
    client = Groq(
        api_key=settings.GROQ_API_KEY.get_secret_value(),
        timeout=settings.GROQ_TIMEOUT_SECONDS,
    )

    try:
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        COMPLAINT_CORRECTION_SYSTEM_PROMPT
                    ),
                },
                {
                    "role": "user",
                    "content": build_complaint_correction_prompt(
                        user_message=user_message,
                        existing_complaint=existing_complaint,
                    ),
                },
            ],
            temperature=0,
            max_completion_tokens=1200,
            response_format={
                "type": "json_object",
            },
        )

    except RateLimitError as exc:
        raise AIServiceError(
            "Groq rate limit reached."
        ) from exc

    except APITimeoutError as exc:
        raise AIServiceError(
            "Groq correction request timed out."
        ) from exc

    except APIConnectionError as exc:
        raise AIServiceError(
            "Unable to connect to Groq."
        ) from exc

    except APIStatusError as exc:
        raise AIServiceError(
            f"Groq correction request failed: {exc.status_code}"
        ) from exc

    content = completion.choices[0].message.content

    if not content:
        raise AIResponseValidationError(
            "Correction model returned an empty response."
        )

    parsed = _parse_correction_json(content)

    updates = parsed.get("field_updates", {})

    if not isinstance(updates, dict):
        updates = {}

    parsed["field_updates"] = _normalize_field_updates(
        updates
    )

    try:
        return ComplaintCorrectionResult.model_validate(
            parsed
        )
    except ValidationError as exc:
        logger.error(
            "Correction validation error: %s",
            exc,
        )

        raise AIResponseValidationError(
            "Correction response has an invalid structure."
        ) from exc