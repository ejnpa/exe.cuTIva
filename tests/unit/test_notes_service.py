from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from executiva.notes.service import NoteService

class FakeRepository:
    def __init__(self, note = None):
        self.note = note
        self.add_like_call= None
        self.remove_like_call= None

    def get_by_id(self, note_id: str):
        return self.note

    def add_like(self, note_id: str, user_id: int):
        self.add_like_call = (note_id, user_id)

    def remove_like(self, note_id: str, user_id: int):
        self.remove_like_call = (note_id, user_id)

    def count_likes(self, note_id: str) -> int:
        return 3


class FakeStorage:
    def __init__(self, file_bytes : bytes = b'Conteudo do ficheiro'):
        self.file_bytes = file_bytes
        self.downloaded_filename = None

    def download_files_from_storage(self, filename: str) -> bytes:
        self.downloaded_filename = filename
        return self.file_bytes

def make_note():
    return SimpleNamespace(
        id="nota-123",
        title="Apontamentos de teste",
        subject="Programação",
        author="aluno@example.pt",
        file_url="https://storage.example.pt/notas/documento.pdf",
        thumbnail_url=None,
    )

def test_read_note_content_extract_file_text(monkeypatch):
    note = make_note()
    repository = FakeRepository(note=note)
    storage = FakeStorage()
    service = NoteService(repo=repository, storage=storage)

    def fake_extract_text(file_bytes, filename):
        assert file_bytes == b"Conteudo do ficheiro"
        assert filename == "documento.pdf"
        return "Texto extraído do ficheiro"

    monkeypatch.setattr("executiva.notes.service.extract_text_from_file", fake_extract_text)

    result = service.read_note_content("nota-123")

    assert result is not None
    assert result["id"] == "nota-123"
    assert result["content"] == "Texto extraído do ficheiro"
    assert storage.downloaded_filename == "documento.pdf"

def test_read_note_content_returns_none_when_does_not_exist(monkeypatch):
    repository = FakeRepository(note=None)
    service = NoteService(repo=repository, storage=FakeStorage())

    result = service.read_note_content("inexistente")

    assert result is None

def test_like_note_uses_user_id_and_returns_updated_count():
    repository = FakeRepository(note=make_note())
    service = NoteService(repo=repository, storage=FakeStorage())

    result = service.like_note("nota-123", user_id=17)

    assert repository.add_like_call == ("nota-123", 17)
    assert result == {"liked": True, "likes_count": 3}

def test_like_note_returns_404_if_note_does_not_exist():
    repository = FakeRepository(note=None)
    service = NoteService(repo=repository, storage=FakeStorage())

    with pytest.raises(HTTPException) as error:
        service.like_note("inexistente", user_id=17)

    assert error.value.status_code == 404


def test_delete_like_removes_like_and_returns_updated_count():
    repository = FakeRepository(note=make_note())
    service = NoteService(repo=repository, storage=FakeStorage())

    result = service.delete_like("nota-123", user_id=17)

    assert repository.remove_like_call == ("nota-123", 17)
    assert result == {"liked": False, "likes_count": 3}


def test_delete_like_returns_404_if_note_does_not_exist():
    repository = FakeRepository(note=None)
    service = NoteService(repo=repository, storage=FakeStorage())

    with pytest.raises(HTTPException) as error:
        service.delete_like("inexistente", user_id=17)

    assert error.value.status_code == 404

