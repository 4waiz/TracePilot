"""TracePilot API client - wraps all backend REST calls."""

import requests
import streamlit as st

API_BASE = "http://localhost:8000"


class APIClient:
    """Thin wrapper around the TracePilot backend API."""

    def __init__(self, base_url: str = API_BASE):
        self.base_url = base_url.rstrip("/")

    def _headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def _get(self, path: str, token: str, params: dict | None = None):
        try:
            r = requests.get(
                f"{self.base_url}{path}", headers=self._headers(token),
                params=params, timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except requests.HTTPError as exc:
            detail = ""
            try:
                detail = exc.response.json().get("detail", str(exc))
            except Exception:
                detail = str(exc)
            st.error(f"API error: {detail}")
            return None
        except requests.ConnectionError:
            st.error("Cannot reach the backend API. Is the server running?")
            return None

    def _post(self, path: str, token: str | None = None, json: dict | None = None,
              data: dict | None = None, files=None):
        try:
            headers = self._headers(token) if token else {}
            r = requests.post(
                f"{self.base_url}{path}", headers=headers,
                json=json, data=data, files=files, timeout=120,
            )
            r.raise_for_status()
            if r.status_code == 204:
                return True
            return r.json()
        except requests.HTTPError as exc:
            detail = ""
            try:
                detail = exc.response.json().get("detail", str(exc))
            except Exception:
                detail = str(exc)
            st.error(f"API error: {detail}")
            return None
        except requests.ConnectionError:
            st.error("Cannot reach the backend API. Is the server running?")
            return None

    def _put(self, path: str, token: str, json: dict | None = None):
        try:
            r = requests.put(
                f"{self.base_url}{path}", headers=self._headers(token),
                json=json, timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except requests.HTTPError as exc:
            detail = ""
            try:
                detail = exc.response.json().get("detail", str(exc))
            except Exception:
                detail = str(exc)
            st.error(f"API error: {detail}")
            return None
        except requests.ConnectionError:
            st.error("Cannot reach the backend API. Is the server running?")
            return None

    def _patch(self, path: str, token: str, json: dict | None = None):
        try:
            r = requests.patch(
                f"{self.base_url}{path}", headers=self._headers(token),
                json=json, timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except requests.HTTPError as exc:
            detail = ""
            try:
                detail = exc.response.json().get("detail", str(exc))
            except Exception:
                detail = str(exc)
            st.error(f"API error: {detail}")
            return None
        except requests.ConnectionError:
            st.error("Cannot reach the backend API. Is the server running?")
            return None

    def _delete(self, path: str, token: str):
        try:
            r = requests.delete(
                f"{self.base_url}{path}", headers=self._headers(token), timeout=30,
            )
            r.raise_for_status()
            return True
        except requests.HTTPError as exc:
            detail = ""
            try:
                detail = exc.response.json().get("detail", str(exc))
            except Exception:
                detail = str(exc)
            st.error(f"API error: {detail}")
            return False
        except requests.ConnectionError:
            st.error("Cannot reach the backend API. Is the server running?")
            return False

    # -- auth ---------------------------------------------------------------

    def login(self, username: str, password: str):
        return self._post(
            "/api/auth/login",
            data={"username": username, "password": password},
        )

    def get_me(self, token: str):
        return self._get("/api/auth/me", token)

    # -- jobs ---------------------------------------------------------------

    def create_job(self, token: str, title: str, sensitivity: str):
        return self._post("/api/jobs/", token, json={
            "title": title, "sensitivity_label": sensitivity,
        })

    def list_jobs(self, token: str, skip: int = 0, limit: int = 50):
        return self._get("/api/jobs/", token, params={"skip": skip, "limit": limit})

    def get_job(self, token: str, job_id: int):
        return self._get(f"/api/jobs/{job_id}", token)

    def update_job_status(self, token: str, job_id: int, status: str):
        return self._patch(f"/api/jobs/{job_id}/status", token, json={"status": status})

    def get_job_summary(self, token: str, job_id: int):
        return self._get(f"/api/jobs/{job_id}/summary", token)

    # -- documents ----------------------------------------------------------

    def upload_documents(self, token: str, job_id: int, files):
        file_tuples = [("files", (f.name, f.getvalue(), "application/pdf")) for f in files]
        return self._post(f"/api/documents/upload/{job_id}", token, files=file_tuples)

    def get_documents(self, token: str, job_id: int):
        return self._get(f"/api/documents/job/{job_id}", token)

    # -- extraction ---------------------------------------------------------

    def trigger_extraction(self, token: str, job_id: int):
        return self._post(f"/api/extraction/{job_id}/extract", token)

    # -- specs --------------------------------------------------------------

    def get_specs(self, token: str, job_id: int):
        return self._get(f"/api/extraction/{job_id}/specs", token)

    def update_spec(self, token: str, spec_id: int, data: dict):
        return self._put(f"/api/extraction/specs/{spec_id}", token, json=data)

    def delete_spec(self, token: str, spec_id: int):
        return self._delete(f"/api/extraction/specs/{spec_id}", token)

    def add_spec(self, token: str, job_id: int, data: dict):
        return self._post(f"/api/extraction/{job_id}/specs", token, json=data)

    def confirm_specs(self, token: str, job_id: int):
        return self._post(f"/api/extraction/{job_id}/confirm", token)

    # -- steps --------------------------------------------------------------

    def get_steps(self, token: str, job_id: int):
        return self._get(f"/api/extraction/{job_id}/steps", token)

    # -- measurements -------------------------------------------------------

    def submit_measurement(self, token: str, job_id: int, spec_id: int, value: float):
        return self._post("/api/inspection/measure", token, json={
            "job_id": job_id, "spec_id": spec_id, "actual_value": value,
        })

    def get_measurements(self, token: str, job_id: int):
        return self._get(f"/api/inspection/{job_id}/measurements", token)

    def delete_measurement(self, token: str, measurement_id: int):
        return self._delete(f"/api/inspection/measurements/{measurement_id}", token)

    # -- progress -----------------------------------------------------------

    def get_progress(self, token: str, job_id: int):
        return self._get(f"/api/inspection/{job_id}/progress", token)

    # -- deviations ---------------------------------------------------------

    def get_deviations(self, token: str, job_id: int):
        return self._get(f"/api/deviations/{job_id}", token)

    def update_deviation(self, token: str, deviation_id: int, data: dict):
        return self._patch(f"/api/deviations/{deviation_id}", token, json=data)

    def approve_deviation(self, token: str, deviation_id: int, data: dict):
        return self._post(f"/api/deviations/{deviation_id}/approve", token, json=data)

    # -- reports ------------------------------------------------------------

    def generate_report(self, token: str, job_id: int):
        return self._post(f"/api/reports/{job_id}/generate", token)

    def get_report_pdf_url(self, job_id: int):
        return f"{self.base_url}/api/reports/{job_id}/download/pdf"

    def get_report_json_url(self, job_id: int):
        return f"{self.base_url}/api/reports/{job_id}/download/json"

    # -- audit --------------------------------------------------------------

    def get_audit_logs(self, token: str, filters: dict | None = None):
        return self._get("/api/audit/", token, params=filters)


# Module-level singleton
api = APIClient()
