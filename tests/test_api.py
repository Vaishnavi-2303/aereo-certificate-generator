import pytest
from fastapi.testclient import TestClient

from app import main
from app.database import SessionLocal
from app.models import GenerationJob, Recipient


@pytest.fixture(autouse=True)
def clean_db():
    db = SessionLocal()
    db.query(Recipient).delete()
    db.query(GenerationJob).delete()
    db.commit()
    db.close()
    yield


def client():
    return TestClient(main.app)


def payload():
    return {"recipients": [
        {"name": "Anita Rao", "email": "anita@example.com", "course": "Python Fundamentals", "completion_date": "2026-10-08"},
        {"name": "Rahul Kumar", "email": "rahul@example.com", "course": "FastAPI Basics", "completion_date": "2026-10-08"},
    ]}


def test_create_generation_job():
    response = client().post("/api/jobs/", json=payload())
    assert response.status_code == 202
    data = response.json()
    assert data["total"] == 2
    assert data["job_id"]


def test_input_validation():
    bad = {"recipients": [{"name": "", "course": "", "completion_date": "2026-10-08"}]}
    response = client().post("/api/jobs/", json=bad)
    assert response.status_code == 422


def test_certificate_generation_and_status():
    response = client().post("/api/jobs/", json=payload())
    assert response.status_code == 202
    data = response.json()
    status = client().get(f"/api/jobs/{data['job_id']}")
    assert status.status_code == 200
    result = status.json()
    assert result["status"] == "completed"
    assert result["successful"] == 2
    assert all(r["status"] == "success" for r in result["recipients"])


def test_individual_certificate_failure_does_not_stop_job(monkeypatch):
    original = main.generate_certificate

    def failing_generator(recipient, output_path):
        if recipient.name == "Rahul Kumar":
            raise RuntimeError("simulated rendering failure")
        original(recipient, output_path)

    monkeypatch.setattr(main, "generate_certificate", failing_generator)
    response = client().post("/api/jobs/", json=payload())
    assert response.status_code == 202
    job = response.json()
    data = client().get(f"/api/jobs/{job['job_id']}").json()
    assert data["status"] == "completed"
    assert data["successful"] == 1
    assert data["failed"] == 1
    failed = next(r for r in data["recipients"] if r["name"] == "Rahul Kumar")
    assert failed["status"] == "failed"
    assert "simulated" in failed["error"]


def test_retrieve_generated_certificate():
    response = client().post("/api/jobs/", json=payload())
    job = response.json()
    data = client().get(f"/api/jobs/{job['job_id']}").json()
    recipient = data["recipients"][0]
    download = client().get(f"/api/certificates/{data['job_id']}/{recipient['id']}")
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert download.content[:4] == b"%PDF"
