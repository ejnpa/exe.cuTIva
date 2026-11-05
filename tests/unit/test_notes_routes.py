from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from executiva.core.dependencies import get_notes_service
from executiva.core.security import get_current_user
from executiva.notes.router import router as notes_router


class FakeNotesService:
    def __init__(self, note=None):
        self.note = note
        self.like_call = None
        self.delete_like_call = None

    def like_note(self, note_id: str, user_id: int):
        self.like_call = (note_id, user_id)
        return {"liked": True, "likes_count": 4}

    def get_note_by_id(self, note_id: str):
        return self.note

    def delete_like(self, note_id: str, user_id: int):
        self.delete_like_call = (note_id, user_id)
        return {"liked": False, "likes_count": 3}


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

    with TestClient(app) as client:
        yield client, current_user, notes_service

    app.dependency_overrides.clear()


def test_like_route_passes_user_id(test_context):
    client, current_user, notes_service = test_context

    response = client.post("/api/notes/nota-123/like")

    assert response.status_code == 200
    assert response.json() == {"liked": True, "likes_count": 4}
    assert notes_service.like_call == ("nota-123", current_user.id)


def test_view_route_denies_another_users_note(test_context):
    client, current_user, notes_service = test_context
    notes_service.note = SimpleNamespace(
        id="nota-456",
        author="outro@example.pt",
    )

    response = client.get("/api/notes/nota-456/view")

    assert response.status_code == 403

def test_delete_like_route_passes_user_id(test_context):
    client, current_user, notes_service = test_context

    response = client.delete("/api/notes/nota-123/like")

    assert response.status_code == 200
    assert response.json() == {"liked": False, "likes_count": 3}
    assert notes_service.delete_like_call == ("nota-123", current_user.id)