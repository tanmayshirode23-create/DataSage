import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def signup(email, name="Test User", password="secret123"):
    r = client.post("/api/auth/signup", json={"name": name, "email": email, "password": password})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def alice():
    return signup("alice@example.com", "Alice")


@pytest.fixture(scope="module")
def sample_dataset(alice):
    r = client.post("/api/datasets/sample", headers=alice)
    assert r.status_code == 201, r.text
    return r.json()


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_signup_duplicate_and_validation(alice):
    r = client.post("/api/auth/signup", json={"name": "A", "email": "alice@example.com", "password": "secret123"})
    assert r.status_code == 409
    r = client.post("/api/auth/signup", json={"name": "B", "email": "not-an-email", "password": "secret123"})
    assert r.status_code == 422
    r = client.post("/api/auth/signup", json={"name": "B", "email": "b@example.com", "password": "123"})
    assert r.status_code == 422


def test_login(alice):
    ok = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "secret123"})
    assert ok.status_code == 200 and ok.json()["user"]["name"] == "Alice"
    bad = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "wrong"})
    assert bad.status_code == 401
    assert client.get("/api/datasets").status_code == 401  # no token
    assert client.get("/api/datasets", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_sample_report_matches_original_app(sample_dataset):
    assert sample_dataset["quality_score"] == 87.7
    assert sample_dataset["score_label"] == "Needs light cleanup"
    assert sample_dataset["total_rows"] == 1000
    report = sample_dataset["report"]
    assert sum(i["count"] for i in report["issue_summary"]) == report["issue_count"]
    assert report["recommendations"]


def test_upload_custom_csv_and_bad_files(alice):
    csv = "customer_id,email,phone,signup_date\n1,a@x.com,+1-555-123-4567,2026-01-01\n1,bad-email,12,not a date\n"
    r = client.post("/api/datasets", headers=alice, files={"file": ("tiny.csv", csv, "text/csv")})
    assert r.status_code == 201, r.text
    body = r.json()
    summary = {i["issue"]: i["count"] for i in body["report"]["issue_summary"]}
    assert summary["Duplicate IDs"] == 1
    assert summary["Invalid emails"] == 1
    assert summary["Invalid phones"] == 1
    assert summary["Date issues"] == 1

    assert client.post("/api/datasets", headers=alice, files={"file": ("x.txt", "a,b", "text/plain")}).status_code == 400
    assert client.post("/api/datasets", headers=alice, files={"file": ("e.csv", "", "text/csv")}).status_code == 400
    assert client.post("/api/datasets", headers=alice, files={"file": ("h.csv", "a,b\n", "text/csv")}).status_code == 400


def test_custom_rules_override_detection(alice):
    csv = "id,mail_addr,notes\n1,a@x.com,hi\n2,broken,hi\n"
    r = client.post("/api/datasets", headers=alice, files={"file": ("rules.csv", csv, "text/csv")},
                    data={"rules": '{"email_columns": ["mail_addr"], "id_column": "id"}'})
    assert r.status_code == 201, r.text
    summary = {i["issue"]: i["count"] for i in r.json()["report"]["issue_summary"]}
    assert summary["Invalid emails"] == 1
    bad = client.post("/api/datasets", headers=alice, files={"file": ("r.csv", csv, "text/csv")},
                      data={"rules": '{"hack": 1}'})
    assert bad.status_code == 400


def test_list_issues_preview_and_filters(alice, sample_dataset):
    ds_id = sample_dataset["id"]
    all_issues = client.get(f"/api/datasets/{ds_id}/issues", headers=alice).json()
    assert all_issues["total"] > 0 and len(all_issues["items"]) == 25

    emails = client.get(f"/api/datasets/{ds_id}/issues", headers=alice, params={"issue_type": "invalid_email"}).json()
    expected = next(i["count"] for i in sample_dataset["report"]["issue_summary"] if i["issue"] == "Invalid emails")
    assert emails["total"] == expected
    assert all(i["issue_type"] == "invalid_email" for i in emails["items"])

    preview = client.get(f"/api/datasets/{ds_id}/preview", headers=alice, params={"rows": 10}).json()
    assert len(preview["rows"]) == 10 and "customer_id" in preview["columns"]


def test_cleaned_csv_improves_score(alice, sample_dataset):
    r = client.get(f"/api/datasets/{sample_dataset['id']}/cleaned", headers=alice)
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    cleaned = pd.read_csv(io.BytesIO(r.content))
    assert len(cleaned) < sample_dataset["total_rows"]
    assert not cleaned.duplicated().any()
    assert not cleaned["customer_id"].duplicated().any()

    again = client.post("/api/datasets", headers=alice, files={"file": ("sample_customer_data.csv", r.content, "text/csv")})
    assert again.json()["quality_score"] > sample_dataset["quality_score"]


def test_trends_group_by_filename(alice, sample_dataset):
    series = client.get("/api/datasets/trends", headers=alice).json()
    top = series[0]
    assert top["filename"] == "sample_customer_data.csv" and len(top["points"]) >= 2
    assert top["points"][-1]["score"] > top["points"][0]["score"]


def test_users_cannot_see_each_others_data(alice, sample_dataset):
    bob = signup("bob@example.com", "Bob")
    ds_id = sample_dataset["id"]
    for path in (f"/api/datasets/{ds_id}", f"/api/datasets/{ds_id}/issues",
                 f"/api/datasets/{ds_id}/preview", f"/api/datasets/{ds_id}/cleaned"):
        assert client.get(path, headers=bob).status_code == 404
    assert client.delete(f"/api/datasets/{ds_id}", headers=bob).status_code == 404
    assert client.get("/api/datasets", headers=bob).json() == []


def test_alert_threshold(alice, sample_dataset):
    assert client.patch("/api/auth/me", headers=alice, json={"alert_threshold": 95}).status_code == 200
    listing = client.get("/api/datasets", headers=alice).json()
    assert any(d["below_threshold"] for d in listing)
    assert client.patch("/api/auth/me", headers=alice, json={"alert_threshold": 150}).status_code == 422
    client.patch("/api/auth/me", headers=alice, json={"alert_threshold": 70})


def test_delete_dataset(alice):
    created = client.post("/api/datasets/sample", headers=alice).json()
    assert client.delete(f"/api/datasets/{created['id']}", headers=alice).status_code == 204
    assert client.get(f"/api/datasets/{created['id']}", headers=alice).status_code == 404
