"""
Reusable validation helpers for patient data.

These are deliberately kept as pure functions (no DB, no FastAPI)
so they can be reused by:
  - Pydantic schemas (schemas.py)
  - The Vapi tool route (routes/vapi.py)
  - Unit tests
"""
from datetime import datetime
import re

import phonenumbers
from phonenumbers import NumberParseException


# All 50 US states + DC (2-letter codes)
US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}

# Alphabetic + hyphens + apostrophes + spaces, 1-50 chars
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z\-' ]{0,49}$")

# ZIP: 5 digits or ZIP+4 (5-4)
ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")

# Email: simple but strict enough (Pydantic EmailStr handles the rest)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_us_phone(value: str) -> str:
    """Validate and normalize a U.S. 10-digit phone number.

    Returns the E.164 format (e.g. +14155551234).
    Raises ValueError with a clear message if invalid.
    """
    if not value:
        raise ValueError("Phone number is required")
    try:
        parsed = phonenumbers.parse(value, "US")
    except NumberParseException:
        raise ValueError("Invalid phone number format")

    if not phonenumbers.is_valid_number(parsed):
        raise ValueError("Not a valid U.S. phone number")

    if parsed.country_code != 1:
        raise ValueError("Only U.S. phone numbers are accepted")

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def validate_date_of_birth(value: str) -> str:
    """Validate MM/DD/YYYY date, not in the future, not absurdly old.

    Returns the same string if valid.
    """
    if not value:
        raise ValueError("Date of birth is required")
    try:
        dob = datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError:
        raise ValueError("Date of birth must be in MM/DD/YYYY format")

    today = datetime.utcnow().date()
    if dob > today:
        raise ValueError("Date of birth cannot be in the future")

    # Sanity: nobody alive is > 130 years old
    age = (today - dob).days / 365.25
    if age > 130:
        raise ValueError("Date of birth is not realistic")

    return value


def validate_state(value: str) -> str:
    """Validate 2-letter U.S. state code (uppercase)."""
    if not value:
        raise ValueError("State is required")
    v = value.strip().upper()
    if v not in US_STATE_CODES:
        raise ValueError(f"'{value}' is not a valid 2-letter U.S. state code")
    return v


def validate_zip(value: str) -> str:
    """Validate 5-digit or ZIP+4 U.S. ZIP code."""
    if not value:
        raise ValueError("ZIP code is required")
    v = value.strip()
    if not ZIP_RE.match(v):
        raise ValueError("ZIP code must be 5 digits or ZIP+4 (e.g. 94103 or 94103-1234)")
    return v


def validate_name(value: str, field: str = "Name") -> str:
    """Validate a 1-50 character name with letters, hyphens, apostrophes."""
    if not value:
        raise ValueError(f"{field} is required")
    v = value.strip()
    if not NAME_RE.match(v):
        raise ValueError(
            f"{field} must be 1-50 characters, letters/hyphens/apostrophes only"
        )
    return v


def validate_email(value: str) -> str:
    """Validate a basic email format. Empty is allowed (optional field)."""
    if not value:
        return ""
    v = value.strip()
    if not EMAIL_RE.match(v):
        raise ValueError("Invalid email format")
    return v.lower()


def validate_sex(value: str) -> str:
    """Validate the sex enum."""
    allowed = {"Male", "Female", "Other", "Decline to Answer"}
    if not value:
        raise ValueError("Sex is required")
    v = value.strip()
    # Case-insensitive match to be friendly to the LLM's capitalization
    for option in allowed:
        if option.lower() == v.lower():
            return option
    raise ValueError(f"Sex must be one of: {', '.join(sorted(allowed))}")