# Voice AI Agent — Patient Registration System

A voice-based AI agent that answers real phone calls, collects standard U.S. patient demographic information through natural conversation, persists records to PostgreSQL, and exposes them via a REST API.

Built for a 3-hour technical assessment.

---

## Architecture

```text
[Caller on Phone]
        │
        ▼
[Vapi Voice Agent] ← STT (Soniox) + TTS (ElevenLabs) + LLM (OpenAI GPT-4o-mini)
        │
        │ POST /vapi/tools/register-patient
        ▼
[FastAPI Backend on Render] ← Pydantic v2 validation, SQLAlchemy ORM
        │
        │ INSERT
        ▼
[PostgreSQL on Neon]

[Reviewer] ──► GET /patients ──► [FastAPI on Render] ──► [Neon Postgres]
```

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| **Telephony + Voice** | Vapi (with Soniox STT + ElevenLabs TTS) | Fastest way to provision a real U.S. number and conversational loop without building STT/TTS |
| **LLM** | OpenAI GPT-4o-mini (via Vapi, own key) | Fast, cheap, reliable function-calling |
| **Backend** | FastAPI (Python 3.11) | Native async, built-in Pydantic, auto OpenAPI docs |
| **Validation** | Pydantic v2 + `phonenumbers` library | Real FCC-derived phone validation, not regex |
| **Database** | PostgreSQL on Neon (free tier) | Cloud-hosted, survives restarts, SSL by default |
| **ORM** | SQLAlchemy (sync) | Simple, predictable, no async complexity for this scale |
| **API Hosting** | Render (free tier) | Simple Python deploy, env vars managed in dashboard |

---

## Project Structure

```text
patient-registration/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app, lifespan, router includes
│   ├── config.py          # Settings loader (env vars)
│   ├── database.py        # SQLAlchemy engine, SessionLocal, Base, get_db
│   ├── models.py          # Patient model
│   ├── schemas.py         # PatientCreate, PatientUpdate, PatientOut (Pydantic)
│   ├── validators.py      # phone, DOB, state, ZIP, name, email helpers
│   └── routes/
│       ├── __init__.py
│       ├── patients.py    # REST CRUD endpoints
│       └── vapi.py        # Vapi tool-call webhook
├── seed.py                # Optional: seed 2 demo patients
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Local Setup

### 1. Clone & install

```bash
git clone <your-repo-url>
cd patient-registration
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

### 2. Set environment variables

Copy `.env.example` to `.env` and fill in:

```env
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
OPENAI_API_KEY=sk-...
VAPI_WEBHOOK_SECRET=optional
LOG_LEVEL=INFO
```

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string (Neon pooled URL with `?sslmode=require`) |
| `OPENAI_API_KEY` | Yes | OpenAI API key (used by Vapi, not by this server) |
| `VAPI_WEBHOOK_SECRET` | No | Optional shared secret for Vapi webhook (not currently enforced) |
| `LOG_LEVEL` | No | Python logging level (default: INFO) |

### 3. Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

Tables are created automatically on startup.

### 4. (Optional) Seed demo data

```bash
python seed.py
```

### 5. Open the API docs

Visit http://127.0.0.1:8000/docs.

---

## API Endpoints

All responses use the envelope: `{"data": ..., "error": null}`

| Method | Endpoint | Description |
|---|---|---|
| GET | `/patients` | List all non-deleted patients. Optional filters: `?last_name=`, `?date_of_birth=`, `?phone_number=` |
| GET | `/patients/{patient_id}` | Fetch one patient by UUID |
| POST | `/patients` | Create a new patient. Returns the created record with `patient_id` |
| PUT | `/patients/{patient_id}` | Partial update — only fields in the request body are changed |
| DELETE | `/patients/{patient_id}` | Soft delete — sets `deleted_at`, does not remove the row |
| POST | `/vapi/tools/register-patient` | Webhook for Vapi tool calls (used by the voice agent) |
| GET | `/health` | Health check |

### Example: Create a patient

```bash
curl -X POST <API_BASE_URL>/patients \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Jane",
    "last_name": "Doe",
    "date_of_birth": "01/15/1990",
    "sex": "Female",
    "phone_number": "4155551234",
    "address_line_1": "123 Main St",
    "city": "San Francisco",
    "state": "CA",
    "zip_code": "94103"
  }'
```

Response (201):

```json
{
  "data": {
    "patient_id": "98b10010-d34a-4874-a37c-06455271d9d1",
    "first_name": "Jane",
    "last_name": "Doe",
    "phone_number": "+14155551234",
    "state": "CA",
    ...
  },
  "error": null
}
```

Note: `phone_number` is stored in E.164 format after normalization. `state` is upper-cased.

---

## Data Model

| Field | Type | Validation | Required |
|---|---|---|---|
| `patient_id` | UUID | Auto-generated | Auto |
| `first_name` | String(50) | 1–50 chars, alphabetic + hyphens/apostrophes | Yes |
| `last_name` | String(50) | Same as above | No |
| `date_of_birth` | String(10) | MM/DD/YYYY, not future, not >130 years old | Yes |
| `sex` | String(20) | Male, Female, Other, Decline to Answer | Yes |
| `phone_number` | String(20) | Valid U.S. 10-digit (via `phonenumbers`) | Yes |
| `email` | String(254) | Valid email format | No |
| `address_line_1` | String(200) | — | Yes |
| `address_line_2` | String(200) | — | No |
| `city` | String(100) | 1–100 chars | Yes |
| `state` | String(2) | Valid U.S. state code | Yes |
| `zip_code` | String(10) | 5-digit or ZIP+4 | Yes |
| `insurance_provider` | String(200) | — | No |
| `insurance_member_id` | String(100) | — | No |
| `preferred_language` | String(50) | Default "English" | No |
| `emergency_contact_name` | String(200) | — | No |
| `emergency_contact_phone` | String(20) | Valid U.S. 10-digit | No |
| `created_at` | Timestamp (UTC) | Auto | Auto |
| `updated_at` | Timestamp (UTC) | Auto on write | Auto |
| `deleted_at` | Timestamp (UTC) | Set on soft delete | Auto |

---

## Voice Agent Behavior

The voice agent (Vapi) uses a system prompt that enforces:

- **Natural conversation**, not a rigid form
- **One question at a time**, warm acknowledgments between
- **Real-time field checks** — the LLM uses its own judgment to catch obviously wrong values (e.g., a phone number with 11 digits) and re-ask before moving on
- **Backend validation as the final gate** — if the LLM misses something, the backend returns a "Please correct the following: ..." message and the LLM re-asks only the affected field
- **Confirmation before saving** — the agent reads back every collected field and waits for explicit "yes"
- **Graceful error handling** — invalid input never causes silence

### Sample interaction (real call transcript)

Transcript of an actual test call, taken from the Vapi call log.

```text
Agent:  Hello.
Caller: Hello.

Agent:  Thank you for calling. My name is Aria. I'm the intake coordinator here. I can help you register as a new patient today. May I start with your first and last name?
Caller: Uh, yeah, sure. My name is William Cooper.

Agent:  Great, thank you, William. Could you please tell me your date of birth?
Caller: It's 19 March 19. 85.

Agent:  Just to confirm. Confirm, that's March 19, 1985, correct?
Caller: Yeah, correct.

Agent:  Thanks. How do you identify? You can say male. Female, other. Or. You can decline to answer.
Caller: Yeah, mail, definitely.

Agent:  Got it, male. And what's your phone number?
Caller: Uh, it's 412 55. 5. 0100.

Agent:  I'm sorry. That doesn't look like a valid U.S. phone number. Could you give me all 10 digits?
Caller: Yeah, I said it again: 412. 555. 0100.

Agent:  Thanks for that. Just to confirm, that's 412-5. 55-0100, is that right?
Caller: Yeah, definitely.

Agent:  Perfect. Now, could you please provide your street address?
Caller: It's 999 S. T.

Agent:  Could you please.
Caller: San Francisco.

Agent:  Thanks. Now, what state are you in? You can just give me the 2-letter abbreviation.
Caller: Basically California.

Agent:  Okay, so that's C-A for California, and could you please provide your ZIP code?
Caller: It's 94103.

Agent:  Great, thank you. Now, I can also collect your insurance information: emergency contact and preferred language. Would you like to provide any of those?
Caller: Uh, yeah, if you ask. Preferred language. It's English. And I don't have any emergency. Contact number or. Insurance policy. Number.

Agent:  Got it, English for your preferred language. Just to confirm, you don't have an emergency contact or insurance information? Correct?
Caller: Yeah, correct.

Agent:  Thank you for confirming. Now. Let me read back everything I've collected to make sure it's all correct. Your. Name. Is William Cooper. Date. Of birth March. 19, 1985. You. Identify as male. And your phone number is 412-5. 55-0. 100. You live at 999 ST. Santa. Francisco, California with. ZIP code. 9. 41. 0. 3. Your preferred language is English, and you don't have an emergency contact or insurance. Information. Is everything correct?

[Tool: Register Patient — completed successfully]

Caller: Yeah, definitely.

Agent:  One moment while I save your information. I've successfully saved your information.
Caller: Okay, thank you.

Agent:  You're all set, William. Thanks for calling. And take care.
```

---

## Testing

### Manual API testing

Open the Swagger docs at `<API_BASE_URL>/docs` and exercise each endpoint.

### Validation coverage

Use these test payloads to verify the validation layer:

**Invalid phone (3 digits):**

```json
{"phone_number": "123", ...}
```

→ `422 Unprocessable Entity` with message about invalid U.S. phone.

**Future date of birth:**

```json
{"date_of_birth": "01/01/2099", ...}
```

→ `422` — "Date of birth cannot be in the future".

**Invalid state:**

```json
{"state": "XX", ...}
```

→ `422` — "'XX' is not a valid 2-letter U.S. state code".

**Invalid ZIP:**

```json
{"zip_code": "abc", ...}
```

→ `422` — ZIP code error.

**Valid fictional phone numbers (for testing without a real phone):**

- `4125550100` (Pittsburgh)
- `4155550101` (San Francisco)
- `2125550102` (New York)
- `6505550104` (Palo Alto)

These are in the officially-reserved 555-01XX fictional-use range.

---

## Trade-offs & Design Decisions

### 1. `date_of_birth` stored as `String(10)`, not a native Date

**Decision:** Store as MM/DD/YYYY string.

**Why:** The spec explicitly requires MM/DD/YYYY. A native Date column loses the format intent and introduces timezone parsing edge cases. Our validator enforces correctness on the way in; the DB stores exactly what was confirmed by the caller.

### 2. Phone number is indexed, not unique

**Decision:** `phone_number` has an index but no UNIQUE constraint.

**Why:** In real U.S. healthcare, multiple patients legitimately share a phone (family members, group homes). The spec only requires "valid U.S. 10-digit phone", not unique. Uniqueness is enforced by `patient_id` (UUID), as required.

### 3. Soft delete, not hard delete

**Decision:** `DELETE /patients/{id}` sets `deleted_at`; the row remains in the DB.

**Why:** Required by the spec ("do not hard-delete"). Also matches healthcare data-retention norms.

### 4. Sync SQLAlchemy, not async

**Decision:** Used sync `Session` throughout.

**Why:** At this scale (dozens of patients, one concurrent call at a time), async adds complexity with no user-visible benefit. Sync is more predictable and easier to debug under time pressure.

### 5. Duplicate detection removed

**Decision:** Backend does not check for existing patients by phone; every call creates a new record.

**Why:** The bonus feature caused reliability issues in testing. When the tool returned a "would you like to update?" message instead of a save confirmation, the LLM sometimes misinterpreted it as success and told the caller the information was saved. Removing it made the tool deterministic: it always saves, or it always returns a validation error. Duplicate detection is documented here as a known limitation / next step.

### 6. LLM does lightweight real-time checks; backend is authoritative

**Decision:** The prompt allows the LLM to catch obviously wrong values (11-digit phone, future DOB, missing @ in email) but the backend validates everything again.

**Why:** Belt-and-suspenders. The LLM catches the obvious stuff fast, improving UX. The backend catches anything the LLM misses (e.g., invalid area codes). The LLM is explicitly told not to guess about subtle validity (like whether `123` is a valid phone exchange) — only the backend knows that.

### 7. Database on Neon, API on Render

**Decision:** Separate hosting for DB and API.

**Why:** Neon provides a serverless Postgres with a generous free tier and SSL by default. Render provides a simple Python deploy for the API. Separating them means each can be scaled or replaced independently, and the DB survives API restarts/redeploys.

---

## Known Limitations & Next Steps

### Known limitations

1. **No duplicate detection** — see trade-off #5 above. A caller can register twice with the same phone.
2. **No authentication** — the REST API is open. Fine for a technical assessment, not production.
3. **No HIPAA compliance** — out of scope per the challenge instructions. Do not store real patient data.
4. **`last_name` search uses `func.replace`** for apostrophe/hyphen tolerance — this bypasses the DB index. Fine for this dataset, but should be replaced with a generated normalized column at scale.

### Next steps (if more time)

1. **Duplicate detection via early lookup** — add a `find_patient_by_phone` Vapi tool (backed by a `/vapi/tools/find-patient` endpoint) that runs right after the caller gives their phone, and offer to update instead of create.
2. **Automated tests** — pytest for validators, schemas, and the API layer.
3. **Simple HTML dashboard** — a static page that lists patients from `/patients`.
4. **Multi-language support** — detect "Hablo español" and switch the system prompt.
5. **Call transcript storage** — persist Vapi's transcript against `patient_id`.

---

## Author

**SYED WASIF ALI**
<syedwasifali2136@gmail.com>