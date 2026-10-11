import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Patient(Base):
    __tablename__ = "patients"

    # Primary key
    patient_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # Required fields
    first_name = Column(String(50), nullable=False)
    date_of_birth = Column(String(10), nullable=False)  # MM/DD/YYYY as string
    sex = Column(String(20), nullable=False)
    phone_number = Column(String(20), nullable=False, index=True)
    address_line_1 = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    zip_code = Column(String(10), nullable=False)

    # Optional fields
    last_name = Column(String(50), nullable=True)
    email = Column(String(254), nullable=True)
    address_line_2 = Column(String(200), nullable=True)
    insurance_provider = Column(String(200), nullable=True)
    insurance_member_id = Column(String(100), nullable=True)
    preferred_language = Column(String(50), nullable=False, default="English")
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)

    # Audit fields
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Patient {self.patient_id} {self.first_name} {self.last_name}>"