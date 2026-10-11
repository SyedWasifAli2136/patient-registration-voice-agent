"""
Seed 1-2 demo patient records.

Run once:  python seed.py
Safe to re-run: it skips if patients already exist.
"""
from app.database import SessionLocal, Base, engine
from app.models import Patient
from app.schemas import PatientCreate
from app.routes.patients import create_patient_record
from pydantic import ValidationError


SEED_PATIENTS = [
    {
        "first_name": "John",
        "last_name": "Smith",
        "date_of_birth": "03/22/1985",
        "sex": "Male",
        "phone_number": "2125557890",
        "email": "john.smith@example.com",
        "address_line_1": "456 Oak Ave",
        "address_line_2": "Apt 12B",
        "city": "New York",
        "state": "NY",
        "zip_code": "10001",
        "insurance_provider": "Blue Cross",
        "insurance_member_id": "BC123456789",
        "preferred_language": "English",
        "emergency_contact_name": "Mary Smith",
        "emergency_contact_phone": "2125557891",
    },
    {
        "first_name": "Maria",
        "last_name": "Garcia",
        "date_of_birth": "07/04/1992",
        "sex": "Female",
        "phone_number": "3055551234",
        "email": "maria.garcia@example.com",
        "address_line_1": "789 Palm Blvd",
        "city": "Miami",
        "state": "FL",
        "zip_code": "33101",
        "preferred_language": "Spanish",
    },
]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(Patient).filter(Patient.deleted_at.is_(None)).count()
        if existing > 0:
            print(f"DB already has {existing} patients. Skipping seed.")
            return

        for raw in SEED_PATIENTS:
            try:
                payload = PatientCreate(**raw)
                patient = create_patient_record(db, payload)
                print(f"Seeded: {patient.first_name} {patient.last_name} ({patient.patient_id})")
            except ValidationError as e:
                print(f"Skipping invalid seed {raw['first_name']}: {e}")

        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()