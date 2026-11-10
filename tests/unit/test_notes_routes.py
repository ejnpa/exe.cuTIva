from types import SimpleNamespace

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from executiva.core.dependencies import get_notes_service
from executiva.core.security import get_current_user
from executiva.notes.router import router as notes_router
pytestmark = pytest.mark.anyio

class FakeNotesService:
    def __init__(self, note=None):
        self.note = note
        self.like_call = None
        self.delete_like_call = None
        self.storage = SimpleNamespace(download_files_from_storage=lambda name: b"png")

    def like_note(self, note_id: str, user_id: int):
        self.like_call = (note_id, user_id)
        return {"liked": True, "likes_count": 4}

    def get_note_by_id(self, note_id: str):
        return self.note

    def delete_like(self, note_id: str, user_id: int):
        self.delete_like_call = (note_id, user_id)
        return {"liked": False, "likes_count": 3}

    # Imita o método do NoteService real usado pela rota /view.
    # Os bytes e o nome fixos tornam o resultado do teste previsível.
    def prepare_download(self, note_id: str):
        return {
            "bytes": b"pdf de teste",
            "filename": "documento.pdf",
        }


@pytest.fixture
async def api_client(test_context):
    app, _, _ = test_context
    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
    )as client:
        yield client


@pytest.fixture
def test_context():
    """Cria uma API isolada e injeta utilizador e serviço falsos."""
    app = FastAPI()
    app.include_router(notes_router)

    current_user = SimpleNamespace(
        id=17,
        email="dono@example.pt",
    )
    notes_service = FakeNotesService()

    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_notes_service] = lambda: notes_service


    yield app, current_user, notes_service

    app.dependency_overrides.clear()


async def test_like_route_passes_user_id(test_context, api_client):
    _, current_user, notes_service = test_context

    response = await api_client.post("/api/notes/nota-123/like")

    assert response.status_code == 200
    assert response.json() == {"liked": True, "likes_count": 4}
    assert notes_service.like_call == ("nota-123", current_user.id)


async def test_view_route_allows_another_authenticated_user(test_context, api_client):
    _, _, notes_service = test_context
    notes_service.note = SimpleNamespace(
        id="nota-456",
        author="outro@example.pt",
    )

    response = await api_client.get("/api/notes/nota-456/view")

    # A leitura é partilhada; a eliminação continua protegida pelo serviço.
    assert response.status_code == 200
    assert response.content == b"pdf de teste"
    assert response.headers["content-disposition"] == "inline"

async def test_delete_like_route_passes_user_id(test_context, api_client):
    _, current_user, notes_service = test_context

    response = await api_client.delete("/api/notes/nota-123/like")

    assert response.status_code == 200
    assert response.json() == {"liked": False, "likes_count": 3}
    assert notes_service.delete_like_call == ("nota-123", current_user.id)


async def test_thumbnail_route_devolve_png_a_outro_utilizador_autenticado(
    test_context, api_client
):
    _, _, notes_service = test_context
    notes_service.note = SimpleNamespace(
        id="nota-partilhada",
        author="outro@example.pt",
        thumbnail_url="https://storage.test/thumb_nota.png",
    )

    response = await api_client.get("/api/notes/nota-partilhada/thumbnail")

    assert response.status_code == 200
    assert response.content == b"png"
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "private, max-age=3600"


async def test_thumbnail_route_devolve_404_quando_nao_ha_miniatura(
    test_context, api_client
):
    _, _, notes_service = test_context
    notes_service.note = SimpleNamespace(
        id="nota-sem-miniatura",
        author="dono@example.pt",
        thumbnail_url=None,
    )

    response = await api_client.get("/api/notes/nota-sem-miniatura/thumbnail")

    assert response.status_code == 404


async def test_thumbnail_route_devolve_404_quando_blob_esta_em_falta(
    test_context, api_client
):
    _, _, notes_service = test_context
    notes_service.note = SimpleNamespace(
        id="nota-blob-em-falta",
        author="dono@example.pt",
        thumbnail_url="https://storage.test/thumb_falta.png",
    )
    notes_service.storage = SimpleNamespace(
        download_files_from_storage=lambda name: (_ for _ in ()).throw(
            FileNotFoundError(name)
        )
    )

    response = await api_client.get("/api/notes/nota-blob-em-falta/thumbnail")

    assert response.status_code == 404
    assert response.json()["detail"] == "Miniatura não encontrada"
