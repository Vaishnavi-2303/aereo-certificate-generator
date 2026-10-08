from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .certificate import OUTPUT_DIR, generate_certificate
from .database import Base, SessionLocal, engine
from .models import GenerationJob, Recipient
from .schemas import GenerationRequest, GenerationResponse, RecipientResult

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Bulk Certificate Generator API", version="1.0.0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def process_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if not job:
            return
        job.status = "processing"
        db.commit()

        for recipient in job.recipients:
            if recipient.status != "pending":
                continue
            try:
                filename = f"{job_id}_{recipient.id}.pdf"
                output_path = OUTPUT_DIR / filename
                generate_certificate(recipient, output_path)
                recipient.status = "success"
                recipient.file_name = filename
                job.successful += 1
            except Exception as exc:
                recipient.status = "failed"
                recipient.error = str(exc)[:500]
                job.failed += 1
            db.commit()

        job.status = "completed"
        job.completed_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


def build_response(job: GenerationJob) -> GenerationResponse:
    results = []
    for recipient in job.recipients:
        results.append(RecipientResult(
            id=recipient.id,
            name=recipient.name,
            status=recipient.status,
            error=recipient.error,
            download_url=f"/api/certificates/{job.id}/{recipient.id}" if recipient.status == "success" else None,
        ))
    return GenerationResponse(
        job_id=job.id,
        status=job.status,
        total=job.total,
        successful=job.successful,
        failed=job.failed,
        recipients=results,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/jobs/", response_model=GenerationResponse, status_code=202)
def create_job(payload: GenerationRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job_id = str(uuid4())
    job = GenerationJob(id=job_id, total=len(payload.recipients), successful=0, failed=0, status="queued")
    db.add(job)
    db.flush()

    for item in payload.recipients:
        db.add(Recipient(
            job_id=job_id,
            name=item.name,
            email=str(item.email) if item.email else None,
            course=item.course,
            completion_date=item.completion_date.isoformat(),
            status="pending",
        ))
    db.commit()
    db.refresh(job)
    background_tasks.add_task(process_job, job_id)
    return build_response(job)


@app.get("/api/jobs/{job_id}", response_model=GenerationResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return build_response(job)


@app.get("/api/certificates/{job_id}/{recipient_id}")
def get_certificate(job_id: str, recipient_id: int, db: Session = Depends(get_db)):
    recipient = db.query(Recipient).filter(Recipient.job_id == job_id, Recipient.id == recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Certificate record not found")
    if recipient.status != "success" or not recipient.file_name:
        raise HTTPException(status_code=409, detail="Certificate is not available")
    path = OUTPUT_DIR / recipient.file_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Generated certificate file not found")
    return FileResponse(path, media_type="application/pdf", filename=path.name)
