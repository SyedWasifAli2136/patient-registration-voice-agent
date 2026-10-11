"""
Pydantic schemas for the Patient resource.

Three schemas:
  - PatientCreate  : for POST /patients (all fields, validations applied)
  - PatientUpdate  : for PUT /patients/{id} (all optional, partial updates)
  - PatientOut     : for API responses (matches the DB row)

Uses the validators from app/validators.py so validation logic is not duplicated.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.validators import (
    validate_date_of_birth,
    validate_email,
    validate_name,
    validate_sex,
    validate_state,
    validate_us_phone,
    validate_zip,
)


# ============================================================
# Shared validator functions (reused across all schemas)
# ============================================================

def _check_first_name(v):
    return validate_name(v, "First name")

def _check_last_name(v):
    if v is None or v == "":
        return None
    return validate_name(v, "Last name")

def _check_dob(v):
    if v is None:
        return None
    return validate_date_of_birth(v)

def _check_sex(v):
    if v is None:
        return None
    return validate_sex(v)

def _check_phone(v):
    if v is None:
        return None
    return validate_us_phone(v)

def _check_email(v):
    if v is None or v == "":
        return None
    return validate_email(str(v))

def _check_state(v):
    if v is None:
        return None
    return validate_state(v)

def _check_zip(v):
    if v is None:
        return None
    return validate_zip(v)

def _check_ec_phone(v):
    if v is None or v == "":
        return None
    return validate_us_phone(v)

def _check_ec_name(v):
    if v is None or v == "":
        return None
    return validate_name(v, "Emergency contact name")


# ============================================================
# PatientCreate — used for POST /patients and the Vapi tool
# ============================================================

class PatientCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    date_of_birth: str = Field(..., description="MM/DD/YYYY")
    sex: str = Field(..., description="Male | Female | Other | Decline to Answer")
    phone_number: str = Field(..., description="U.S. 10-digit phone")
    email: Optional[EmailStr] = None
    address_line_1: str = Field(..., min_length=1, max_length=200)
    address_line_2: Optional[str] = Field(None, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str = Field(..., min_length=5, max_length=10)
    insurance_provider: Optional[str] = Field(None, max_length=200)
    insurance_member_id: Optional[str] = Field(None, max_length=100)
    preferred_language: Optional[str] = Field("English", max_length=50)
    emergency_contact_name: Optional[str] = Field(None, max_length=200)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)

    _v_first_name = field_validator("first_name")(_check_first_name)
    _v_last_name  = field_validator("last_name")(_check_last_name)
    _v_dob        = field_validator("date_of_birth")(_check_dob)
    _v_sex        = field_validator("sex")(_check_sex)
    _v_phone      = field_validator("phone_number")(_check_phone)
    _v_email      = field_validator("email", mode="before")(_check_email)
    _v_state      = field_validator("state")(_check_state)
    _v_zip        = field_validator("zip_code")(_check_zip)
    _v_ec_phone   = field_validator("emergency_contact_phone")(_check_ec_phone)
    _v_ec_name    = field_validator("emergency_contact_name")(_check_ec_name)


# ============================================================
# PatientUpdate — used for PUT /patients/{id} (partial update)
# ============================================================

class PatientUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    date_of_birth: Optional[str] = None
    sex: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    address_line_1: Optional[str] = Field(None, max_length=200)
    address_line_2: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    zip_code: Optional[str] = Field(None, max_length=10)
    insurance_provider: Optional[str] = Field(None, max_length=200)
    insurance_member_id: Optional[str] = Field(None, max_length=100)
    preferred_language: Optional[str] = Field(None, max_length=50)
    emergency_contact_name: Optional[str] = Field(None, max_length=200)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)

    _v_first_name = field_validator("first_name")(_check_first_name)
    _v_last_name  = field_validator("last_name")(_check_last_name)
    _v_dob        = field_validator("date_of_birth")(_check_dob)
    _v_sex        = field_validator("sex")(_check_sex)
    _v_phone      = field_validator("phone_number")(_check_phone)
    _v_email      = field_validator("email", mode="before")(_check_email)
    _v_state      = field_validator("state")(_check_state)
    _v_zip        = field_validator("zip_code")(_check_zip)
    _v_ec_phone   = field_validator("emergency_contact_phone")(_check_ec_phone)
    _v_ec_name    = field_validator("emergency_contact_name")(_check_ec_name)


# ============================================================
# PatientOut — API response schema
# ============================================================

class PatientOut(BaseModel):
    patient_id: UUID
    first_name: str
    last_name: Optional[str] = None
    date_of_birth: str
    sex: str
    phone_number: str
    email: Optional[EmailStr] = None
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: str
    zip_code: str
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: Optional[str] = "English"
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True