"""
Vapi tool-call webhook.

Vapi sends tool calls from the LLM to this endpoint. We:
  1. Validate the arguments (same validators used by the REST API).
  2. Save the patient via the shared service function.
  3. Return Vapi's expected {"results": [...]} shape.

The 'result' string is spoken by the agent, so it's written conversationally.

On validation or DB errors, we still return HTTP 200 — but with an error
message in 'result' — so the agent can gracefully speak the failure to the
caller instead of going silent.
"""
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.schemas import PatientCreate
from app.routes.patients import create_patient_record

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vapi/tools", tags=["vapi"])


# ---------- Helpers ----------

def _format_validation_error(errors: List[Dict[str, Any]]) -> str:
    """Turn Pydantic errors into a caller-friendly sentence the agent can speak."""
    field_label = {
        "first_name": "first name",
        "last_name": "last name",
        "date_of_birth": "date of birth",
        "sex": "sex",
        "phone_number": "phone number",
        "email": "email",
        "address_line_1": "street address",
        "address_line_2": "apartment or unit",
        "city": "city",
        "state": "state",
        "zip_code": "ZIP code",
        "insurance_provider": "insurance provider",
        "insurance_member_id": "insurance member ID",
        "preferred_language": "preferred language",
        "emergency_contact_name": "emergency contact name",
        "emergency_contact_phone": "emergency contact phone",
    }
    messages = []
    for err in errors:
        loc = err.get("loc", [])
        field = loc[-1] if loc else "field"
        label = field_label.get(field, field)
        raw_msg = err.get("msg", "is invalid")
        # Strip Pydantic's "Value error, " prefix
        msg = raw_msg.replace("Value error, ", "")
        messages.append(f"{label}: {msg}")
    return "Please correct the following: " + "; ".join(messages)


def _extract_tool_calls(body: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Pull tool calls out of Vapi's payload, tolerating shape variations."""
    msg = body.get("message", body)
    return msg.get("toolCalls") or msg.get("toolCallList") or []


def _result(tool_call_id: str, text: str) -> Dict[str, Any]:
    return {"toolCallId": tool_call_id, "result": text}


# ---------- Endpoint ----------

@router.post("/register-patient")
async def register_patient(request: Request):
    """
    Vapi tool endpoint: register a new patient.

    Always returns HTTP 200 with a 'results' array — success or failure —
    because non-200 responses cause Vapi to drop the call silently.
    """
    try:
        body = await request.json()
    except Exception:
        logger.exception("Vapi sent invalid JSON")
        return {"results": [_result("unknown", "Sorry, I couldn't read that. Please try again.")]}

    logger.info("=== VAPI REQUEST ===")
    logger.info("Headers: %s", dict(request.headers))
    logger.info("Body (full): %s", body)

    tool_calls = _extract_tool_calls(body)
    if not tool_calls:
        logger.warning("No tool calls in Vapi payload")
        return {"results": [_result("unknown", "I didn't receive any registration information.")]}

    results = []
    db: Session = SessionLocal()
    try:
        for call in tool_calls:
            call_id = call.get("id", "unknown")
            func = call.get("function", {}) or {}
            name = func.get("name", "")
            args = func.get("arguments", {}) or {}

            # Handle unexpected tool name gracefully
            if name != "register_patient":
                results.append(_result(call_id, f"Unknown tool '{name}'."))
                continue

            # Vapi sometimes sends arguments as a JSON string — parse it if so
            if isinstance(args, str):
                import json
                try:
                    args = json.loads(args)
                except Exception:
                    logger.warning("Could not parse arguments string: %s", args)
                    args = {}
                    
            # ---- Validate ----
            try:
                payload = PatientCreate(**args)
            except ValidationError as e:
                msg = _format_validation_error(e.errors())
                logger.warning("Validation failed for Vapi tool call: %s", msg)
                results.append(_result(call_id, msg))
                continue

            # ---- Persist ----
            try:
                patient = create_patient_record(db, payload)
                msg = (
                    f"Patient registered successfully. "
                    f"Patient ID is {patient.patient_id}. "
                    f"{patient.first_name} {patient.last_name or ''}".strip()
                    + " has been added to our system."
                )
                results.append(_result(call_id, msg))
                logger.info("Registered patient %s via Vapi", patient.patient_id)
            except Exception as e:
                logger.exception("DB write failed for Vapi tool call")
                db.rollback()
                results.append(_result(
                    call_id,
                    "I'm sorry, I'm having trouble saving your information right now. "
                    "Please try again in a moment or call back later.",
                ))
    finally:
        db.close()

    response = {"results": results}
    logger.info("=== VAPI RESPONSE ===")
    logger.info("Body: %s", response)
    return response