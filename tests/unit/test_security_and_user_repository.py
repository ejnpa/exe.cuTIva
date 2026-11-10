from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from executiva.core.config import settings
from executiva.core.security import (
    ALGORITHM,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from executiva.db.base import Base
from executiva.users.models import User
from executiva.users.repository import UserRepository


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(
        User(
            id=1,
            username="Ana",
            email="ana@example.pt",
            password=get_password_hash("palavra-passe-segura"),
        )
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def request_with_cookie(token=None):
    headers = []
    if token is not None:
        headers.append((b"cookie", f"access_token={token}".encode()))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": headers,
            "server": ("test", 80),
            "client": ("test", 1234),
        }
    )


def test_password_hash_nao_e_texto_simples_e_pode_ser_verificado():
    password = "palavra-passe-segura"
    password_hash = get_password_hash(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("outra-palavra-passe", password_hash)


def test_create_access_token_assina_subject_e_expiracao():
    token = create_access_token({"sub": "ana@example.pt"})
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])

    assert payload["sub"] == "ana@example.pt"
    assert payload["exp"] > datetime.now(timezone.utc).timestamp()


def test_user_repository_procura_e_devolve_none(db_session):
    repository = UserRepository(db_session)

    assert repository.get_by_email("ana@example.pt").username == "Ana"
    assert repository.get_by_email("ausente@example.pt") is None


def test_user_repository_cria_utilizador(db_session):
    repository = UserRepository(db_session)
    user = repository.create(
        {
            "username": "Bruno",
            "email": "bruno@example.pt",
            "password": "hash-falso",
        }
    )

    assert user.id is not None
    assert repository.get_by_email("bruno@example.pt").username == "Bruno"


def test_get_current_user_aceita_cookie_com_token_valido(db_session):
    token = create_access_token({"sub": "ana@example.pt"})

    user = get_current_user(request_with_cookie(token), db_session)

    assert user.email == "ana@example.pt"


@pytest.mark.parametrize("token", [None, "token-invalido"])
def test_get_current_user_rejeita_cookie_ausente_ou_token_invalido(
    db_session, token
):
    with pytest.raises(HTTPException) as error:
        get_current_user(request_with_cookie(token), db_session)

    assert error.value.status_code == 401


def test_get_current_user_rejeita_token_expirado(db_session):
    token = jwt.encode(
        {
            "sub": "ana@example.pt",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.secret_key,
        algorithm=ALGORITHM,
    )

    with pytest.raises(HTTPException) as error:
        get_current_user(request_with_cookie(token), db_session)

    assert error.value.status_code == 401


def test_get_current_user_rejeita_subject_sem_utilizador(db_session):
    token = create_access_token({"sub": "ausente@example.pt"})

    with pytest.raises(HTTPException) as error:
        get_current_user(request_with_cookie(token), db_session)

    assert error.value.status_code == 401


def test_get_current_user_rejeita_subject_em_formato_invalido(db_session):
    token = create_access_token({"sub": 42})

    with pytest.raises(HTTPException) as error:
        get_current_user(request_with_cookie(token), db_session)

    assert error.value.status_code == 401
