from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from executiva.artifacts.router import router as artifacts_router
from executiva.core.dependencies import (
    get_generated_artifact_service,
    get_notes_service,
)
from executiva.core.security import get_current_user

pytestmark = pytest.mark.anyio


class FakeNotesService:
    def __init__(self, note=None, content="Texto da nota"):
        self.note = note
        self.content = content
        self.read_ids = []

    def get_note_by_id(self, note_id):
        return self.note if self.note and self.note.id == note_id else None

    def read_note_content(self, note_id):
        self.read_ids.append(note_id)
        return {"content": self.content} if self.note else None


class FakeCache:
    def __init__(self):
        self.pins = []

    def pin(self, user_id, cache_key):
        self.pins.append((user_id, cache_key))


class FakeArtifacts:
    def __init__(self, error=None):
        self.cache = FakeCache()
        self.error = error
        self.summaries = []
        self.audios = []

    def get_or_create_summary(self, note_id, content):
        if self.error:
            raise self.error
        self.summaries.append((note_id, content))
        return "Resumo", "chave-resumo"

    async def get_or_create_audio(self, note_id, variant, text):
        if self.error:
            raise self.error
        self.audios.append((note_id, variant, text))
        return b"mp3", "chave-audio"


@pytest.fixture
def library_context():
    app = FastAPI()
    app.include_router(artifacts_router)
    user = SimpleNamespace(id=7, email="ana@example.pt")
    note = SimpleNamespace(id="nota-1", author=user.email)
    notes = FakeNotesService(note=note)
    artifacts = FakeArtifacts()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_notes_service] = lambda: notes
    app.dependency_overrides[get_generated_artifact_service] = lambda: artifacts
    yield app, user, note, notes, artifacts
    app.dependency_overrides.clear()


@pytest.fixture
async def api_client(library_context):
    app, *_ = library_context
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


async def test_guardar_resumo_da_propria_nota(library_context, api_client):
    _, user, _, notes, artifacts = library_context
    client = api_client

    response = await client.post(
        "/api/library/save",
        json={"note_id": "nota-1", "kind": "summary", "variant": "adapted"},
    )

    assert response.status_code == 200
    assert artifacts.summaries == [("nota-1", "Texto da nota")]
    assert artifacts.cache.pins == [(user.id, "chave-resumo")]
    assert notes.read_ids == ["nota-1"]


async def test_guardar_audio_adaptado_gera_resumo_antes_do_audio(
    library_context, api_client
):
    _, user, _, _, artifacts = library_context
    client = api_client

    response = await client.post(
        "/api/library/save",
        json={"note_id": "nota-1", "kind": "audio", "variant": "adapted"},
    )

    assert response.status_code == 200
    assert artifacts.summaries == [("nota-1", "Texto da nota")]
    assert artifacts.audios == [("nota-1", "adapted", "Resumo")]
    assert artifacts.cache.pins == [(user.id, "chave-audio")]


async def test_guardar_artefacto_de_outra_pessoa_e_proibido(
    library_context, api_client
):
    _, _, note, _, artifacts = library_context
    client = api_client
    note.author = "outra@example.pt"

    response = await client.post(
        "/api/library/save",
        json={"note_id": "nota-1", "kind": "summary"},
    )

    assert response.status_code == 403
    assert artifacts.cache.pins == []


async def test_guardar_artefacto_de_nota_inexistente(library_context, api_client):
    _, _, note, _, _ = library_context
    client = api_client
    note.id = "outra-nota"

    response = await client.post(
        "/api/library/save",
        json={"note_id": "nota-1", "kind": "summary"},
    )

    assert response.status_code == 404


async def test_guardar_artefacto_sem_texto_de_origem(library_context, api_client):
    _, _, _, notes, _ = library_context
    client = api_client
    notes.content = ""

    response = await client.post(
        "/api/library/save",
        json={"note_id": "nota-1", "kind": "summary"},
    )

    assert response.status_code == 404


async def test_erro_de_ia_e_convertido_em_502(library_context, api_client):
    _, _, _, _, artifacts = library_context
    client = api_client
    artifacts.error = RuntimeError("IA indisponível")

    response = await client.post(
        "/api/library/save",
        json={"note_id": "nota-1", "kind": "summary"},
    )

    assert response.status_code == 502
    assert "IA indisponível" in response.json()["detail"]


async def test_request_rejeita_kind_invalido(library_context, api_client):
    client = api_client

    response = await client.post(
        "/api/library/save",
        json={"note_id": "nota-1", "kind": "documento"},
    )

    assert response.status_code == 422
