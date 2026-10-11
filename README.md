# Voice AI Agent — Patient Registration System

A voice-based AI agent accessible via a real US phone number that collects
standard US patient demographic information through natural conversation,
persists records to PostgreSQL, and exposes them via a REST API.

## Live Demo

- **Phone Number:** _(fill in after Vapi setup)_
- **API Base URL:** _(fill in after Render deploy)_

## Architecture

[Phone Call] → [Vapi Voice Agent] → [FastAPI Backend] → [Neon PostgreSQL]
                                          ↓
                                     [REST API]

## Stack

- **Voice + Telephony:** Vapi (with OpenAI GPT-4o-mini)
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL on Neon
- **Validation:** Pydantic v2 + `phonenumbers`
- **Hosting:** Render

## Local Setup

1. Clone the repo.
2. Create a virtualenv and install dependencies: