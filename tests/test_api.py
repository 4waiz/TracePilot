"""
Integration tests for the TracePilot API using FastAPI TestClient.
Covers: login flow, job creation, upload, extraction (mocked),
measurement pass/fail, deviation approval, pagination, summary, and
the new measurement-delete endpoint.
"""

import io
import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app
from backend.auth import hash_password
from backend.models import User

# ── Test database (file-based, shared across the session) ────────────────────

_TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_tracepilot.db")
_TEST_DB_URL = f"sqlite:///{_TEST_DB_PATH}"

engine = create_engine(_TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_db():
    """Create a fresh schema + seed users before every test."""
    # Clear the login rate limiter between tests
    from backend.routers.auth_routes import _login_attempts
    _login_attempts.clear()

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    # Seed test users
    for uname, pw, role in [
        ("operator", "operator123", "operator"),
        ("supervisor", "supervisor123", "supervisor"),
        ("admin", "admin123", "admin"),
    ]:
        db.add(User(username=uname, password_hash=hash_password(pw), role=role))
    db.commit()
    db.close()
    yield


def pytest_sessionfinish(session, exitstatus):
    """Clean up test DB file after all tests complete."""
    engine.dispose()
    if os.path.exists(_TEST_DB_PATH):
        try:
            os.remove(_TEST_DB_PATH)
        except OSError:
            pass


def _login(username: str = "operator", password: str = "operator123") -> str:
    """Helper: log in and return the bearer token."""
    r = client.post("/api/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Auth tests ───────────────────────────────────────────────────────────────

class TestAuth:
    def test_login_success(self):
        r = client.post("/api/auth/login", data={"username": "operator", "password": "operator123"})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_invalid_credentials(self):
        r = client.post("/api/auth/login", data={"username": "operator", "password": "wrong"})
        assert r.status_code == 401

    def test_me_endpoint(self):
        token = _login()
        r = client.get("/api/auth/me", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["username"] == "operator"
        assert r.json()["role"] == "operator"

    def test_me_without_token(self):
        r = client.get("/api/auth/me")
        assert r.status_code == 401

    def test_rate_limiting(self):
        """After LOGIN_RATE_LIMIT bad attempts, further attempts are rejected."""
        # Reset the rate limiter state for this test
        from backend.routers.auth_routes import _login_attempts
        _login_attempts.clear()

        for _ in range(5):
            client.post("/api/auth/login", data={"username": "x", "password": "y"})
        r = client.post("/api/auth/login", data={"username": "x", "password": "y"})
        assert r.status_code == 429

        # Clean up so other tests aren't affected
        _login_attempts.clear()


# ── Job tests ────────────────────────────────────────────────────────────────

class TestJobs:
    def test_create_job(self):
        token = _login()
        r = client.post("/api/jobs/", json={
            "title": "Test Job",
            "sensitivity_label": "general",
        }, headers=_auth(token))
        assert r.status_code == 201
        assert r.json()["title"] == "Test Job"
        assert r.json()["status"] == "created"

    def test_list_jobs_with_pagination(self):
        token = _login()
        # Create 3 jobs
        for i in range(3):
            client.post("/api/jobs/", json={"title": f"Job {i}"}, headers=_auth(token))

        # Get all
        r = client.get("/api/jobs/", headers=_auth(token))
        assert r.status_code == 200
        assert len(r.json()) == 3

        # Paginate
        r = client.get("/api/jobs/?skip=0&limit=2", headers=_auth(token))
        assert r.status_code == 200
        assert len(r.json()) == 2

        r = client.get("/api/jobs/?skip=2&limit=2", headers=_auth(token))
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_get_job(self):
        token = _login()
        create_r = client.post("/api/jobs/", json={"title": "Get Test"}, headers=_auth(token))
        job_id = create_r.json()["id"]
        r = client.get(f"/api/jobs/{job_id}", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["id"] == job_id

    def test_status_transition_valid(self):
        token = _login()
        create_r = client.post("/api/jobs/", json={"title": "Transition Test"}, headers=_auth(token))
        job_id = create_r.json()["id"]
        r = client.patch(f"/api/jobs/{job_id}/status", json={"status": "extracting"}, headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["status"] == "extracting"

    def test_status_transition_invalid(self):
        token = _login()
        create_r = client.post("/api/jobs/", json={"title": "Bad Transition"}, headers=_auth(token))
        job_id = create_r.json()["id"]
        r = client.patch(f"/api/jobs/{job_id}/status", json={"status": "completed"}, headers=_auth(token))
        assert r.status_code == 400

    def test_uploading_state_removed(self):
        """'uploading' is no longer a valid transition target."""
        token = _login()
        create_r = client.post("/api/jobs/", json={"title": "No Upload State"}, headers=_auth(token))
        job_id = create_r.json()["id"]
        r = client.patch(f"/api/jobs/{job_id}/status", json={"status": "uploading"}, headers=_auth(token))
        assert r.status_code == 400

    def test_operator_cannot_see_others_jobs(self):
        token_op = _login("operator", "operator123")
        token_sup = _login("supervisor", "supervisor123")
        # Supervisor creates a job
        r = client.post("/api/jobs/", json={"title": "Sup Job"}, headers=_auth(token_sup))
        job_id = r.json()["id"]
        # Operator cannot access it
        r = client.get(f"/api/jobs/{job_id}", headers=_auth(token_op))
        assert r.status_code == 403

    def test_job_summary(self):
        token = _login()
        create_r = client.post("/api/jobs/", json={"title": "Summary Test"}, headers=_auth(token))
        job_id = create_r.json()["id"]
        r = client.get(f"/api/jobs/{job_id}/summary", headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        assert "job" in body
        assert "documents" in body
        assert "specs" in body
        assert "measurements" in body
        assert "deviations" in body
        assert body["job"]["creator_name"] == "operator"


# ── Document upload tests ────────────────────────────────────────────────────

class TestDocumentUpload:
    def test_upload_pdf(self):
        token = _login()
        job_r = client.post("/api/jobs/", json={"title": "Upload Test"}, headers=_auth(token))
        job_id = job_r.json()["id"]

        # Minimal valid PDF bytes
        pdf_bytes = b"%PDF-1.4 fake content"
        r = client.post(
            f"/api/documents/upload/{job_id}",
            files=[("files", ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf"))],
            headers=_auth(token),
        )
        assert r.status_code == 201
        assert len(r.json()) == 1
        assert r.json()[0]["original_filename"] == "test.pdf"

    def test_upload_non_pdf_rejected(self):
        token = _login()
        job_r = client.post("/api/jobs/", json={"title": "Reject Test"}, headers=_auth(token))
        job_id = job_r.json()["id"]

        r = client.post(
            f"/api/documents/upload/{job_id}",
            files=[("files", ("test.txt", io.BytesIO(b"hello"), "text/plain"))],
            headers=_auth(token),
        )
        assert r.status_code == 400

    def test_upload_size_limit(self):
        """Files over MAX_UPLOAD_SIZE_MB should be rejected."""
        token = _login()
        job_r = client.post("/api/jobs/", json={"title": "Size Test"}, headers=_auth(token))
        job_id = job_r.json()["id"]

        # Patch the constant to a tiny value for testing
        import backend.routers.document_routes as doc_mod
        original = doc_mod.MAX_UPLOAD_BYTES
        doc_mod.MAX_UPLOAD_BYTES = 100  # 100 bytes

        try:
            big_pdf = b"%PDF-1.4 " + b"x" * 200
            r = client.post(
                f"/api/documents/upload/{job_id}",
                files=[("files", ("big.pdf", io.BytesIO(big_pdf), "application/pdf"))],
                headers=_auth(token),
            )
            assert r.status_code == 413
        finally:
            doc_mod.MAX_UPLOAD_BYTES = original

    def test_download_document(self):
        token = _login()
        job_r = client.post("/api/jobs/", json={"title": "Download Test"}, headers=_auth(token))
        job_id = job_r.json()["id"]

        pdf_bytes = b"%PDF-1.4 test"
        upload_r = client.post(
            f"/api/documents/upload/{job_id}",
            files=[("files", ("dl.pdf", io.BytesIO(pdf_bytes), "application/pdf"))],
            headers=_auth(token),
        )
        doc_id = upload_r.json()[0]["id"]
        r = client.get(f"/api/documents/{doc_id}/download", headers=_auth(token))
        assert r.status_code == 200


class TestExtraction:
    def test_extract_falls_back_to_pymupdf_when_pdfplumber_fails(self, monkeypatch):
        import backend.routers.extraction_routes as extraction_mod

        token = _login()
        job_r = client.post("/api/jobs/", json={"title": "Extract Test"}, headers=_auth(token))
        job_id = job_r.json()["id"]

        upload_r = client.post(
            f"/api/documents/upload/{job_id}",
            files=[("files", ("demo_sop.pdf", io.BytesIO(b"%PDF-1.4 broken"), "application/pdf"))],
            headers=_auth(token),
        )
        assert upload_r.status_code == 201

        def _broken_pdfplumber(*args, **kwargs):
            raise ValueError("Invalid dictionary construct")

        class _FakePage:
            def get_text(self, mode="text"):
                return "Outer Diameter: 25.400 mm, Tolerance: 0.013"

        class _FakeDoc:
            def __iter__(self):
                return iter([_FakePage()])

            def close(self):
                return None

        monkeypatch.setattr(extraction_mod.pdfplumber, "open", _broken_pdfplumber)
        monkeypatch.setattr(extraction_mod.fitz, "open", lambda *args, **kwargs: _FakeDoc())
        monkeypatch.setattr(extraction_mod, "_build_rag_collection", AsyncMock(return_value=None))
        monkeypatch.setattr(extraction_mod, "_llm_extract", AsyncMock(return_value=None))

        r = client.post(f"/api/extraction/{job_id}/extract", headers=_auth(token))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["method"] == "regex"
        assert body["specs_count"] == 1
        assert body["specs"][0]["characteristic"] == "Outer Diameter"
        assert body["specs"][0]["source_document"] == "demo_sop.pdf"


# ── Measurement + Deviation tests ────────────────────────────────────────────

class TestMeasurementAndDeviation:
    def _create_job_with_confirmed_spec(self, token: str):
        """Helper: create a job with one confirmed spec, status=inspecting."""
        # Create job
        r = client.post("/api/jobs/", json={"title": "Measure Test"}, headers=_auth(token))
        job_id = r.json()["id"]

        # Transition to extracting → review
        client.patch(f"/api/jobs/{job_id}/status", json={"status": "extracting"}, headers=_auth(token))
        client.patch(f"/api/jobs/{job_id}/status", json={"status": "review"}, headers=_auth(token))

        # Add a spec manually
        spec_r = client.post(f"/api/extraction/{job_id}/specs", json={
            "characteristic": "OD",
            "nominal": 25.4,
            "lower_limit": 25.387,
            "upper_limit": 25.413,
            "unit": "mm",
        }, headers=_auth(token))
        spec_id = spec_r.json()["id"]

        # Confirm specs (transitions job to "inspecting")
        client.post(f"/api/extraction/{job_id}/confirm", headers=_auth(token))

        return job_id, spec_id

    def test_measurement_pass(self):
        token = _login()
        job_id, spec_id = self._create_job_with_confirmed_spec(token)
        r = client.post("/api/inspection/measure", json={
            "job_id": job_id, "spec_id": spec_id, "actual_value": 25.400,
        }, headers=_auth(token))
        assert r.status_code == 201
        assert r.json()["passed"] is True
        assert r.json()["deviation"] is None

    def test_measurement_fail_creates_deviation(self):
        token = _login()
        job_id, spec_id = self._create_job_with_confirmed_spec(token)
        r = client.post("/api/inspection/measure", json={
            "job_id": job_id, "spec_id": spec_id, "actual_value": 26.0,
        }, headers=_auth(token))
        assert r.status_code == 201
        assert r.json()["passed"] is False
        assert r.json()["deviation"] is not None
        assert r.json()["deviation"]["status"] == "open"

    def test_deviation_approval(self):
        op_token = _login("operator", "operator123")
        sup_token = _login("supervisor", "supervisor123")
        job_id, spec_id = self._create_job_with_confirmed_spec(op_token)

        # Create a failing measurement
        m_r = client.post("/api/inspection/measure", json={
            "job_id": job_id, "spec_id": spec_id, "actual_value": 26.0,
        }, headers=_auth(op_token))
        dev_id = m_r.json()["deviation"]["id"]

        # Supervisor approves
        r = client.post(f"/api/deviations/{dev_id}/approve", json={
            "disposition": "approved", "notes": "Acceptable variance",
        }, headers=_auth(sup_token))
        assert r.status_code == 201
        assert r.json()["disposition"] == "approved"

    def test_delete_measurement(self):
        token = _login()
        job_id, spec_id = self._create_job_with_confirmed_spec(token)

        # Record a measurement
        m_r = client.post("/api/inspection/measure", json={
            "job_id": job_id, "spec_id": spec_id, "actual_value": 25.400,
        }, headers=_auth(token))
        m_id = m_r.json()["id"]

        # Delete it
        r = client.delete(f"/api/inspection/measurements/{m_id}", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["id"] == m_id

        # Verify it's gone
        r = client.get(f"/api/inspection/{job_id}/measurements", headers=_auth(token))
        assert len(r.json()) == 0

    def test_re_measure_after_delete(self):
        """After deleting a measurement, the spec can be re-measured."""
        token = _login()
        job_id, spec_id = self._create_job_with_confirmed_spec(token)

        # First measurement (fail)
        m_r = client.post("/api/inspection/measure", json={
            "job_id": job_id, "spec_id": spec_id, "actual_value": 26.0,
        }, headers=_auth(token))
        m_id = m_r.json()["id"]

        # Delete and re-measure (pass this time)
        client.delete(f"/api/inspection/measurements/{m_id}", headers=_auth(token))
        r = client.post("/api/inspection/measure", json={
            "job_id": job_id, "spec_id": spec_id, "actual_value": 25.400,
        }, headers=_auth(token))
        assert r.status_code == 201
        assert r.json()["passed"] is True

    def test_progress(self):
        token = _login()
        job_id, spec_id = self._create_job_with_confirmed_spec(token)

        r = client.get(f"/api/inspection/{job_id}/progress", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["total_specs"] == 1
        assert r.json()["measured"] == 0

        # Measure
        client.post("/api/inspection/measure", json={
            "job_id": job_id, "spec_id": spec_id, "actual_value": 25.400,
        }, headers=_auth(token))

        r = client.get(f"/api/inspection/{job_id}/progress", headers=_auth(token))
        assert r.json()["measured"] == 1
        assert r.json()["passed"] == 1


# ── Health check ─────────────────────────────────────────────────────────────

class TestHealth:
    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
