from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from executiva.core.dependencies import (
    get_generated_artifact_service,
    get_notes_service,
)
from executiva.core.security import get_current_user
from executiva.db.session import get_db
from executiva.notes.router import router as notes_router
pytestmark = pytest.mark.anyio

class FakeStorage:
    def __init__(self):
        self.downloaded_filename = None

    def download_files_from_storage(self, filename):
        self.downloaded_filename = filename
        return b"conteudo-do-ficheiro"


class FakeNotesService:


    def __init__(self, note=None, owner_email="dono@example.pt"):
        self.note = note or make_note(owner_email)
        self.storage = FakeStorage()
        self.delete_call = None

    def get_note_by_id(self, note_id):
        if self.note and self.note.id == note_id:
            return self.note
        return None

    def get_filtered_notes(self, school=None, course=None, year=None, subject=None):
        return [make_note("dono@example.pt")]

    def get_my_notes(self, author_email, current_user_id):
        return []

    def read_note_content(self, note_id):
        return {
            "id": note_id,
            "title": "Apontamentos de teste",
            "subject": "Programação",
            "author": self.note.author,
            "file_url": f"/api/notes/{note_id}/view",
            "thumbnail_url": f"/api/notes/{note_id}/thumbnail",
            "content": "Conteúdo de teste suficientemente longo.",
        }

    def prepare_download(self, note_id):
        return {
            "bytes": b"conteudo-do-ficheiro",
            "filename": "documento.pdf",
        }

    def delete_note(self, note_id, current_user_email):
        self.delete_call = (note_id, current_user_email)
        return True

    def like_note(self, note_id, user_id):
        return {"liked": True, "likes_count": 1}

    def delete_like(self, note_id, user_id):
        return {"liked": False, "likes_count": 0}


class FakeArtifactsService:
    def get_or_create_summary(self, note_id, content):
        return "Resumo de teste", False

    async def get_or_create_audio(self, note_id, variant, text):
        return b"audio-de-teste", False


def make_note(author):
    return SimpleNamespace(
        id="nota-123",
        title="Apontamentos de teste",
        school="Escola de teste",
        course="Curso de teste",
        year="1",
        subject="Programação",
        author=author,
        file_url="https://storage.example.pt/notas/documento.pdf",
        thumbnail_url="https://storage.example.pt/notas/thumb_documento.png",
    )


@pytest.fixture
def test_context(monkeypatch):
    app = FastAPI()
    app.include_router(notes_router)

    # O utilizador autenticado é diferente do autor usado nos testes
    # de acesso a documentos alheios.
    current_user = SimpleNamespace(
        id=17,
        email="outro-utilizador@example.pt",
    )

    notes_service = FakeNotesService()
    artifacts_service = FakeArtifactsService()

    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_notes_service] = lambda: notes_service
    app.dependency_overrides[get_generated_artifact_service] = (
        lambda: artifacts_service
    )
    app.dependency_overrides[get_db] = lambda: None

    # A rota adapt devolve o PDF produzido por esta função falsa.
    monkeypatch.setattr(
        "executiva.notes.router.create_acessability_pdf",
        lambda title, summary: b"pdf-de-teste",
    )

    yield app, current_user, notes_service

    app.dependency_overrides.clear()


@pytest.fixture
async def api_client(test_context):
    app, _, _=test_context

    async with AsyncClient(
        transport= ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.mark.parametrize(
    "endpoint",
    [
        "/read",
        "/view",
        "/thumbnail",
        "/download",
        "/adapt",
        "/audio",
    ],
)
# Caracteriza a regra de leitura partilhada: qualquer utilizador autenticado
# pode consultar estes recursos, mesmo que não seja o autor do apontamento.
async def test_outro_utilizador_autenticado_pode_ler_documento(api_client,endpoint):

    response = await api_client.get(f"/api/notes/nota-123{endpoint}")

    assert response.status_code == 200



async def test_lista_apontamentos_e_publica(api_client):
    response = await api_client.get("/api/notes/")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == "nota-123"


async def test_detalhes_do_apontamento_sao_publicos(api_client):

    response = await api_client.get("/api/notes/nota-123")

    assert response.status_code == 200
    assert response.json()["id"] == "nota-123"
    assert response.json()["file_url"] == "/api/notes/nota-123/view"


async def test_detalhes_de_apontamento_inexistente_devolvem_404(
        test_context,
        api_client
):
    _, _, notes_service = test_context
    notes_service.note = None

    response = await api_client.get("/api/notes/inexistente")

    assert response.status_code == 404


async def test_utilizador_autenticado_consegue_ver_os_seus_detalhes(
        test_context,
        api_client
):
    _, current_user, notes_service = test_context
    notes_service.note = make_note(current_user.email)

    response = await api_client.get("/api/notes/nota-123/view")

    assert response.status_code == 200
    assert response.content == b"conteudo-do-ficheiro"
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == "inline"


async def test_miniatura_de_apontamento_proprio(
        test_context,
        api_client
):
    _, current_user, notes_service = test_context
    notes_service.note = make_note(current_user.email)

    response = await api_client.get("/api/notes/nota-123/thumbnail")

    assert response.status_code == 200
    assert response.content == b"conteudo-do-ficheiro"
    assert response.headers["content-type"] == "image/png"
    assert notes_service.storage.downloaded_filename == "thumb_documento.png"


async def test_miniatura_inexistente_devolve_404(
    test_context,
    api_client
):
    _, current_user, notes_service = test_context
    notes_service.note = make_note(current_user.email)
    notes_service.note.thumbnail_url = None

    response = await api_client.get("/api/notes/nota-123/thumbnail")

    assert response.status_code == 404


async def test_download_de_apontamento_proprio(test_context, api_client):
    _, current_user, notes_service = test_context
    notes_service.note = make_note(current_user.email)

    response = await api_client.get("/api/notes/nota-123/download")

    assert response.status_code == 200
    assert response.content == b"conteudo-do-ficheiro"
    assert "attachment" in response.headers["content-disposition"]


async def test_leitura_de_apontamento_proprio(test_context, api_client):
    _, current_user, notes_service = test_context
    notes_service.note = make_note(current_user.email)

    response = await api_client.get("/api/notes/nota-123/read")

    assert response.status_code == 200
    assert response.json()["content"] == (
        "Conteúdo de teste suficientemente longo."
    )


async def test_resumo_adaptado_de_apontamento_proprio(test_context, api_client):
    _, current_user, notes_service = test_context
    notes_service.note = make_note(current_user.email)

    response = await api_client.get("/api/notes/nota-123/adapt")

    assert response.status_code == 200
    assert response.content == b"pdf-de-teste"
    assert response.headers["content-type"] == "application/pdf"


async def test_audio_original_de_apontamento_proprio(test_context, api_client):
    _, current_user, notes_service = test_context
    notes_service.note = make_note(current_user.email)

    response = await api_client.get("/api/notes/nota-123/audio")

    assert response.status_code == 200
    assert response.content == b"audio-de-teste"
    assert response.headers["content-type"] == "audio/mpeg"


async def test_audio_rejeita_tipo_invalido(test_context, api_client):
    _, current_user, notes_service = test_context
    notes_service.note = make_note(current_user.email)

    response = await api_client.get("/api/notes/nota-123/audio?audio_type=inválido")

    assert response.status_code == 422


async def test_eliminacao_delega_com_email_do_utilizador(test_context, api_client):
    _, current_user, notes_service = test_context

    response = await api_client.delete("/api/notes/nota-123")

    assert response.status_code == 200
    assert notes_service.delete_call == (
        "nota-123",
        current_user.email,
    )


async def test_gosto_delega_com_id_do_utilizador(test_context, api_client):
    _, current_user, _ = test_context

    response = await api_client.post("/api/notes/nota-123/like")

    assert response.status_code == 200
    assert response.json() == {"liked": True, "likes_count": 1}


async def test_remocao_de_gosto_delega_com_id_do_utilizador(test_context, api_client):
    _, current_user, _ = test_context

    response = await api_client.delete("/api/notes/nota-123/like")

    assert response.status_code == 200
    assert response.json() == {"liked": False, "likes_count": 0}
