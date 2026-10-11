"""
REST API for the Patient resource.

Endpoints:
  GET    /patients                 -> list all (with optional filters)
  GET    /patients/{patient_id}    -> get one
  POST   /patients                 -> create
  PUT    /patients/{patient_id}    -> partial update
  DELETE /patients/{patient_id}    -> soft delete

All responses use the envelope: {"data": ..., "error": null}
Errors use:                       {"data": null, "error": "..."}
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Patient
from app.schemas import PatientCreate, PatientUpdate, PatientOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patients", tags=["patients"])


# ---------- Helpers ----------

def _envelope(data=None, error=None):
    """Consistent response envelope for every endpoint."""
    return {"data": data, "error": error}


def _get_active_patient_or_404(db: Session, patient_id: UUID) -> Patient:
    """Fetch a non-soft-deleted patient, or raise 404."""
    patient = (
        db.query(Patient)
        .filter(Patient.patient_id == patient_id, Patient.deleted_at.is_(None))
        .first()
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


# ---------- Service layer (shared by REST + Vapi tool) ----------

def create_patient_record(db: Session, payload: PatientCreate) -> Patient:
    """
    Create a new patient row. Shared by POST /patients and the Vapi tool.

    Caller is responsible for handling DB exceptions.
    """
    patient = Patient(
        first_name=payload.first_name,
        last_name=payload.last_name,
        date_of_birth=payload.date_of_birth,
        sex=payload.sex,
        phone_number=payload.phone_number,
        email=payload.email,
        address_line_1=payload.address_line_1,
        address_line_2=payload.address_line_2,
        city=payload.city,
        state=payload.state,
        zip_code=payload.zip_code,
        insurance_provider=payload.insurance_provider,
        insurance_member_id=payload.insurance_member_id,
        preferred_language=payload.preferred_language or "English",
        emergency_contact_name=payload.emergency_contact_name,
        emergency_contact_phone=payload.emergency_contact_phone,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def find_patient_by_phone(db: Session, phone: str) -> Optional[Patient]:
    """Used for duplicate detection (bonus)."""
    return (
        db.query(Patient)
        .filter(Patient.phone_number == phone, Patient.deleted_at.is_(None))
        .first()
    )


# ---------- Endpoints ----------

@router.get("", response_model=None)
def list_patients(
    last_name: Optional[str] = Query(None, description="Filter by last name (case-insensitive)"),
    date_of_birth: Optional[str] = Query(None, description="Filter by DOB in MM/DD/YYYY"),
    phone_number: Optional[str] = Query(None, description="Filter by phone (any format)"),
    db: Session = Depends(get_db),
):
    """List all non-deleted patients. Optional query filters."""
    query = db.query(Patient).filter(Patient.deleted_at.is_(None))

    if last_name:
        # Normalize both sides: strip apostrophes/hyphens/spaces, lowercase.
        # So "obrien" matches "O'Brien", "davis" matches "D'Angelo-Smith", etc.
        normalized_search = last_name.replace("'", "").replace("-", "").replace(" ", "").lower()
        query = query.filter(
            func.replace(func.replace(func.replace(Patient.last_name, "'", ""), "-", ""), " ", "")
            .ilike(f"%{normalized_search}%")
        )
    if date_of_birth:
        query = query.filter(Patient.date_of_birth == date_of_birth)
    if phone_number:
        # Normalize incoming phone for matching (best-effort; falls back to raw)
        from app.validators import validate_us_phone
        try:
            normalized = validate_us_phone(phone_number)
        except ValueError:
            normalized = phone_number
        query = query.filter(Patient.phone_number == normalized)

    patients = query.order_by(Patient.created_at.desc()).all()
    return _envelope(data=[PatientOut.model_validate(p).model_dump(mode="json") for p in patients])


@router.get("/{patient_id}", response_model=None)
def get_patient(patient_id: UUID, db: Session = Depends(get_db)):
    """Fetch a single patient by UUID."""
    patient = _get_active_patient_or_404(db, patient_id)
    return _envelope(data=PatientOut.model_validate(patient).model_dump(mode="json"))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=None)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    """Create a new patient. Returns the created record with patient_id."""
    try:
        patient = create_patient_record(db, payload)
    except Exception as e:
        logger.exception("Failed to create patient")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create patient: {e}",
        )
    return _envelope(data=PatientOut.model_validate(patient).model_dump(mode="json"))


@router.put("/{patient_id}", response_model=None)
def update_patient(
    patient_id: UUID,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
):
    """Partial update. Only fields explicitly provided are changed."""
    patient = _get_active_patient_or_404(db, patient_id)

    # exclude_unset=True -> only fields the caller actually sent
    updates = payload.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(patient, field, value)

    try:
        db.commit()
        db.refresh(patient)
    except Exception as e:
        logger.exception("Failed to update patient")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update patient: {e}",
        )

    return _envelope(data=PatientOut.model_validate(patient).model_dump(mode="json"))


@router.delete("/{patient_id}", response_model=None)
def delete_patient(patient_id: UUID, db: Session = Depends(get_db)):
    """Soft-delete: sets deleted_at, does NOT remove the row."""
    patient = _get_active_patient_or_404(db, patient_id)

    patient.deleted_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(patient)
    except Exception as e:
        logger.exception("Failed to soft-delete patient")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete patient: {e}",
        )

    return _envelope(data={"patient_id": str(patient.patient_id), "deleted_at": patient.deleted_at.isoformat()})