import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import app as flask_app


@pytest.fixture()
def client(tmp_path):
    database = tmp_path / "test.sqlite3"
    flask_app.config.update(TESTING=True, SECRET_KEY="test-secret", DATABASE=str(database))
    with flask_app.app_context():
        from app import init_db
        init_db()
    with flask_app.test_client() as client:
        yield client


def test_home_and_protected_route(client):
    assert client.get("/").status_code == 200
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_register_login_dashboard_logout(client):
    response = client.post("/register", data={"name": "Ana", "email": "ana@example.com", "password": "senha-segura"})
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    response = client.post("/login", data={"email": "ana@example.com", "password": "senha-segura"})
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Ana" in response.get_data(as_text=True)

    response = client.post("/logout")
    assert response.status_code == 302
    assert client.get("/dashboard").status_code == 302


def test_duplicate_email_is_rejected(client):
    payload = {"name": "Ana", "email": "ana@example.com", "password": "senha-segura"}
    client.post("/register", data=payload)
    response = client.post("/register", data=payload)
    assert response.status_code == 200
    assert "já está cadastrado" in response.get_data(as_text=True)
