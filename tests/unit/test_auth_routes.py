from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from http.cookies import SimpleCookie

from executiva.users.router import get_user_service, router as users_router

pytestmark=pytest.mark.anyio

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
def auth_context():
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

    yield app, fake_service

    app.dependency_overrides.clear()

@pytest.fixture
async def api_client(auth_context):
    app, _ = auth_context
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as client:
        yield client


async def test_register_passes_fields_in_correct_order(
        auth_context,
        api_client,
):
    _, fake_service = auth_context

    response = await api_client.post(
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


async def test_login_sets_http_only_cookie(api_client):

    response = await api_client.post(
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


async def test_register_rejeita_email_ja_existente(auth_context, api_client):
    _, fake_service = auth_context
    fake_service.registered_user = None

    response = await api_client.post(
        "/api/auth/register",
        json={
            "username": "Ana",
            "email": "ana@example.pt",
            "password": "palavra-passe-de-teste",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Existe uma conta com este email."


async def test_login_rejeita_credenciais_invalidas(auth_context, api_client):
    _, fake_service = auth_context
    fake_service.token = None

    response = await api_client.post(
        "/api/auth/login",
        data={"username": "ana@example.pt", "password": "errada"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais inválidas."


async def test_logout_remove_cookie_de_sessao(api_client):
    response = await api_client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"message": "Sessão terminada."}

    cookies = SimpleCookie()
    cookies.load(response.headers["set-cookie"])

    assert cookies["access_token"].value == ""
    assert cookies["access_token"]["max-age"] == "0"
