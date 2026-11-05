from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from executiva.users.router import get_user_service, router as users_router


class FakeUserService:
    def __init__(self, registered_user=None, token="jwt-de-teste"):
        self.registered_user = registered_user
        self.token = token
        self.register_call = None

    def register_new_user(self, username, email, password):
        self.register_call = (username, email, password)
        return self.registered_user

    def authenticate_user(self, email, password):
        return self.token


@pytest.fixture
def auth_client():
    app = FastAPI()
    app.include_router(users_router)

    fake_service = FakeUserService(
        registered_user=SimpleNamespace(
            id=1,
            username="Ana",
            email="ana@example.pt",
        )
    )
    app.dependency_overrides[get_user_service] = lambda: fake_service

    with TestClient(app) as client:
        yield client, fake_service

    app.dependency_overrides.clear()


def test_register_passes_fields_in_correct_order(auth_client):
    client, fake_service = auth_client

    response = client.post(
        "/api/auth/register",
        json={
            "username": "Ana",
            "email": "ana@example.pt",
            "password": "palavra-passe-de-teste",
        },
    )

    assert response.status_code == 201
    assert fake_service.register_call == (
        "Ana",
        "ana@example.pt",
        "palavra-passe-de-teste",
    )
    assert "password" not in response.json()


def test_login_sets_http_only_cookie(auth_client):
    client, _ = auth_client

    response = client.post(
        "/api/auth/login",
        data={
            "username": "ana@example.pt",
            "password": "palavra-passe-de-teste",
        },
    )

    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/" in cookie