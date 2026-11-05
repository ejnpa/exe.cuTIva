from types import SimpleNamespace

from executiva.core.security import get_password_hash, verify_password
from executiva.users.service import UserService


class FakeUserRepository:
    def __init__(self, existing_user=None):
        self.user = existing_user
        self.created_user_data = None

    def get_by_email(self, email: str):
        return self.user

    def create(self, user_data: dict):
        self.created_user_data = user_data
        self.user = SimpleNamespace(id=1, **user_data)
        return self.user


def test_register_stores_a_password_hash():
    repository = FakeUserRepository()
    service = UserService(repo=repository)

    user = service.register_new_user(
        "Ana",
        "ana@example.pt",
        "palavra-passe-de-teste",
    )

    assert user.email == "ana@example.pt"
    assert user.password != "palavra-passe-de-teste"
    assert verify_password(
        "palavra-passe-de-teste",
        user.password,
    )


def test_register_returns_none_when_email_already_exists():
    existing_user = SimpleNamespace(email="ana@example.pt")
    repository = FakeUserRepository(existing_user=existing_user)
    service = UserService(repo=repository)

    result = service.register_new_user(
        "Ana",
        "ana@example.pt",
        "palavra-passe-de-teste",
    )

    assert result is None
    assert repository.created_user_data is None


def test_authenticate_returns_token_for_valid_password(monkeypatch):
    user = SimpleNamespace(
        email="ana@example.pt",
        password=get_password_hash("palavra-passe-de-teste"),
    )
    repository = FakeUserRepository(existing_user=user)
    service = UserService(repo=repository)

    monkeypatch.setattr(
        "executiva.users.service.create_access_token",
        lambda data: "token-de-teste",
    )

    token = service.authenticate_user(
        "ana@example.pt",
        "palavra-passe-de-teste",
    )

    assert token == "token-de-teste"


def test_authenticate_returns_none_for_invalid_password():
    user = SimpleNamespace(
        email="ana@example.pt",
        password=get_password_hash("palavra-passe-correta"),
    )
    service = UserService(repo=FakeUserRepository(existing_user=user))

    token = service.authenticate_user(
        "ana@example.pt",
        "palavra-passe-errada",
    )

    assert token is None