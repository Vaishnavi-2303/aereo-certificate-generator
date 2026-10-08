# Bulk Certificate Generator API

A FastAPI backend that accepts one bulk certificate-generation request, validates recipient data, creates one PDF certificate per valid recipient using a predefined template, tracks progress in SQLite, isolates individual failures, and exposes generated certificates for download.

## Tech stack
- Python
- FastAPI
- SQLAlchemy + SQLite
- ReportLab for PDF generation
- Pytest + FastAPI TestClient

## Setup

```powershell
cd aereo_certificate_generator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation, run the commands from Command Prompt instead or allow the local script for the current session.

## Run

```powershell
uvicorn app.main:app --reload
```

Open Swagger UI at `http://127.0.0.1:8000/docs`.

## Run tests

```powershell
pytest -q
```

## API

### Create a bulk generation job

`POST /api/jobs/`

Example body:

```json
{
  "recipients": [
    {
      "name": "Anita Rao",
      "email": "anita@example.com",
      "course": "Python Fundamentals",
      "completion_date": "2026-10-08"
    },
    {
      "name": "Rahul Kumar",
      "email": "rahul@example.com",
      "course": "FastAPI Basics",
      "completion_date": "2026-10-08"
    }
  ]
}
```

The endpoint returns HTTP `202 Accepted` with a `job_id` and current progress. The request supports up to 1,000 recipients.

### Check job status

`GET /api/jobs/{job_id}`

The response includes:
- total recipients
- successful count
- failed count
- overall status
- per-recipient status
- failure reason when available
- download URL for successful certificates

### Retrieve a certificate

`GET /api/certificates/{job_id}/{recipient_id}`

Returns the generated PDF directly.

## Architecture

```text
Client
  |
  | POST /api/jobs/
  v
FastAPI validation
  |
  v
SQLite job + recipient records
  |
  | BackgroundTasks
  v
Certificate processing loop
  |
  +--> ReportLab predefined PDF template
  |
  +--> success -> save PDF + update DB
  |
  +--> failure -> save error + continue next recipient
  |
  v
GET /api/jobs/{job_id}
GET /api/certificates/{job_id}/{recipient_id}
```

## Design decisions

### Why FastAPI?
FastAPI gives automatic request validation, clear API contracts, Swagger documentation, and matches the backend skills expected for the assignment.

### Why SQLite?
The assignment only requires a relational database. SQLite keeps the submission self-contained and easy to run. A production deployment could switch to PostgreSQL using the same SQLAlchemy data-access approach.

### Why background processing?
Certificate rendering can take time when a request contains many recipients. The API creates the job and returns `202 Accepted`, while processing runs in FastAPI background tasks. The client can poll the job endpoint for progress. For a larger production workload, this can be replaced with Celery/RQ and Redis or a managed queue.

### Why isolate individual failures?
Each recipient is processed inside its own `try/except`. A rendering error marks only that recipient as failed and the next recipient continues. This satisfies the bulk-processing requirement without losing successful certificates.

### Template approach
There is exactly one predefined template in `app/certificate.py`. Recipient name, course, and completion date are inserted into that template. A template editor or multiple designs are intentionally not implemented because they are outside the requirement.

## Validation and failure handling

Pydantic validates the incoming request before a job is created. Name and course cannot be blank and have sensible length limits; completion date must be a valid date; email is validated when supplied. During generation, unexpected certificate-rendering errors are stored against the individual recipient.

## Project structure

```text
app/
  certificate.py   # predefined ReportLab certificate template
  database.py      # SQLite/SQLAlchemy setup
  main.py          # API endpoints and background processing
  models.py        # relational database models
  schemas.py       # request/response validation

data/certificates/ # generated PDFs (ignored by Git)
tests/test_api.py
requirements.txt
README.md
```

## Learning and future scope

This project demonstrates FastAPI request validation, relational persistence, background processing, PDF generation, bulk-job design, per-item failure isolation, and API testing.

Future improvements could include Redis + Celery for distributed workers, PostgreSQL, authentication, object storage such as S3, signed download URLs, email delivery, job cancellation/retry, rate limits, structured logging, and a configurable template service.

## Interview talking points

1. The API is bulk-oriented: one request creates one job containing many recipients.
2. `202 Accepted` is used because generation is work that can take time.
3. SQLite stores both job-level and recipient-level state.
4. Each certificate is isolated with its own exception handling, so one failure does not stop the batch.
5. ReportLab generates the predefined PDF template.
6. The background-task approach is intentionally simple; Celery/RQ + Redis would be a stronger production architecture for very large jobs.
