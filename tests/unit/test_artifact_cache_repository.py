from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from executiva.artifacts.cache_repository import GeneratedCacheRepository
from executiva.artifacts.models import GeneratedCache, SavedArtifact
from executiva.db.base import Base
from executiva.notes.models import Notes
from executiva.users.models import User


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(User(id=1, username="Ana", email="ana@example.pt", password="hash"))
    session.add(Notes(
        id="nota-1",
        title="Apontamentos de teste",
        school="Escola",
        course="Curso",
        year="1",
        subject="Programação",
        author="ana@example.pt",
    ))
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def cache_values(**overrides):
    values = {
        "note_id": "nota-1",
        "kind": "summary",
        "variant": "adapted",
        "source_hash": "hash-fonte",
        "result_text": "Resumo de teste",
        "blob_name": None,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    }
    values.update(overrides)
    return values


class FakeStorage:
    def __init__(self):
        self.deleted_audio = []

    def delete_cached_audio(self, blob_name):
        self.deleted_audio.append(blob_name)


def test_save_insere_e_get_atualiza_ultima_utilizacao(db_session):
    repository = GeneratedCacheRepository(db_session, ttl_days=7)
    item = repository.save("cache-1", **cache_values())
    previous_last_used = item.last_used_at

    loaded = repository.get("cache-1")

    assert loaded.cache_key == "cache-1"
    assert loaded.result_text == "Resumo de teste"
    assert loaded.last_used_at >= previous_last_used


def test_save_atualiza_entrada_existente_e_renova_expiracao(db_session):
    repository = GeneratedCacheRepository(db_session, ttl_days=3)
    repository.save(
        "cache-1",
        **cache_values(expires_at=datetime.now(timezone.utc) - timedelta(days=1)),
    )

    updated = repository.save(
        "cache-1",
        **cache_values(result_text="Resumo atualizado"),
    )

    assert updated.result_text == "Resumo atualizado"
    expiry = updated.expires_at
    if expiry.tzinfo is None:  # SQLite devolve DateTime sem fuso horário.
        expiry = expiry.replace(tzinfo=timezone.utc)
    assert expiry > datetime.now(timezone.utc)


def test_get_devolve_none_para_chave_ausente_ou_expirada(db_session):
    repository = GeneratedCacheRepository(db_session, ttl_days=7)
    repository.save(
        "expirada",
        **cache_values(expires_at=datetime.now(timezone.utc) - timedelta(days=1)),
    )

    assert repository.get("inexistente") is None
    assert repository.get("expirada") is None


def test_pin_cria_referencia_para_o_utilizador(db_session):
    repository = GeneratedCacheRepository(db_session, ttl_days=7)
    repository.save("cache-1", **cache_values())

    repository.pin(user_id=1, cache_key="cache-1")

    saved = db_session.query(SavedArtifact).filter_by(
        user_id=1,
        cache_key="cache-1",
    ).one_or_none()
    assert saved is not None
    assert saved.note_title == "Apontamentos de teste"
    assert saved.result_text == "Resumo de teste"


def test_pin_de_artefacto_inexistente_devolve_value_error(db_session):
    repository = GeneratedCacheRepository(db_session, ttl_days=7)

    with pytest.raises(ValueError, match="não existe na cache"):
        repository.pin(user_id=1, cache_key="ausente")


def test_pin_repetido_nao_duplica_referencia(db_session):
    repository = GeneratedCacheRepository(db_session, ttl_days=7)
    repository.save("cache-1", **cache_values())
    repository.pin(user_id=1, cache_key="cache-1")
    repository.pin(user_id=1, cache_key="cache-1")

    assert db_session.query(SavedArtifact).filter_by(
        user_id=1,
        cache_key="cache-1",
    ).count() == 1


def test_artefacto_guardado_nao_expira_ao_fazer_get(db_session):
    repository = GeneratedCacheRepository(db_session, ttl_days=7)
    item = repository.save(
        "cache-1",
        **cache_values(expires_at=datetime.now(timezone.utc) - timedelta(days=1)),
    )
    db_session.add(SavedArtifact(
        user_id=1,
        cache_key="cache-1",
        note_id="nota-1",
        note_title="Nota",
        kind="summary",
        variant="adapted",
        source_hash="hash-fonte",
        result_text="Resumo guardado",
    ))
    db_session.commit()

    assert repository.get("cache-1").cache_key == item.cache_key


def test_unpin_remove_referencia_e_renova_expiracao(db_session):
    repository = GeneratedCacheRepository(db_session, ttl_days=4)
    item = repository.save("cache-1", **cache_values())
    db_session.add(SavedArtifact(
        user_id=1,
        cache_key="cache-1",
        note_id="nota-1",
        note_title="Nota",
        kind="summary",
        variant="adapted",
        source_hash="hash-fonte",
        result_text="Resumo guardado",
    ))
    db_session.commit()

    repository.unpin(user_id=1, cache_key="cache-1")

    assert db_session.query(SavedArtifact).count() == 0
    expiry = item.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    assert expiry > datetime.now(timezone.utc)


def test_delete_expired_remove_audio_nao_guardado_e_preserva_guardado(db_session):
    repository = GeneratedCacheRepository(db_session, ttl_days=7)
    repository.save(
        "audio-expirado",
        **cache_values(
            kind="audio",
            result_text=None,
            blob_name="audio-expirado.mp3",
            expires_at=datetime.now(timezone.utc) - timedelta(days=2),
        ),
    )
    repository.save(
        "resumo-expirado",
        **cache_values(
            expires_at=datetime.now(timezone.utc) - timedelta(days=2),
        ),
    )
    repository.save(
        "audio-guardado",
        **cache_values(
            kind="audio",
            result_text=None,
            blob_name="audio-guardado.mp3",
            expires_at=datetime.now(timezone.utc) - timedelta(days=2),
        ),
    )
    db_session.add(SavedArtifact(
        user_id=1,
        cache_key="audio-guardado",
        note_id="nota-1",
        note_title="Nota",
        kind="audio",
        variant="original",
        source_hash="hash-fonte",
        blob_name="audio-guardado.mp3",
    ))
    db_session.commit()
    storage = FakeStorage()

    deleted = repository.delete_expired(storage)

    assert deleted == 2
    assert storage.deleted_audio == ["audio-expirado.mp3"]
    assert repository.get("audio-guardado") is not None
