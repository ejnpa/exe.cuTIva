from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from executiva.notes.service import NoteService


class FakeRepository:
    def __init__(self, note):
        self.note = note
        self.deleted_note_id = None

    def get_by_id(self, note_id):
        if self.note and self.note.id == note_id:
            return self.note
        return None

    def delete_note(self, note_id):
        self.deleted_note_id = note_id


class FakeStorage:
    def __init__(self):
        self.deleted_files = []

    def delete_file_from_storage(self, filename):
        self.deleted_files.append(filename)


def make_note(author="dono@example.pt"):
    return SimpleNamespace(
        id="nota-123",
        author=author,
        file_url="https://storage.example.pt/docs/ficheiro.pdf",
        thumbnail_url="https://storage.example.pt/thumbs/miniatura.png",
    )


def test_autor_pode_apagar_apontamento_e_ficheiros():
    note = make_note()
    repository = FakeRepository(note)
    storage = FakeStorage()
    service = NoteService(repository, storage)

    result = service.delete_note(
        "nota-123",
        current_user_email="dono@example.pt",
    )

    assert result is True
    assert storage.deleted_files == [
        "ficheiro.pdf",
        "miniatura.png",
    ]
    assert repository.deleted_note_id == "nota-123"


def test_outro_utilizador_nao_pode_apagar_apontamento():
    note = make_note()
    repository = FakeRepository(note)
    storage = FakeStorage()
    service = NoteService(repository, storage)

    with pytest.raises(HTTPException) as error:
        service.delete_note(
            "nota-123",
            current_user_email="outra-pessoa@example.pt",
        )

    assert error.value.status_code == 403
    assert storage.deleted_files == []
    assert repository.deleted_note_id is None


def test_apagar_apontamento_inexistente_devolve_404():
    repository = FakeRepository(note=None)
    storage = FakeStorage()
    service = NoteService(repository, storage)

    with pytest.raises(HTTPException) as error:
        service.delete_note(
            "inexistente",
            current_user_email="dono@example.pt",
        )

    assert error.value.status_code == 404
    assert storage.deleted_files == []
    assert repository.deleted_note_id is None


def test_elimina_apontamento_mesmo_se_falhar_eliminacao_no_storage():
    note = make_note()
    repository = FakeRepository(note)
    storage = FakeStorage()

    def fail_delete(filename):
        raise RuntimeError("Storage indisponível")

    storage.delete_file_from_storage = fail_delete
    service = NoteService(repository, storage)

    result = service.delete_note(
        "nota-123",
        current_user_email="dono@example.pt",
    )

    # O serviço atual ignora falhas ao apagar blobs e continua a apagar
    # o registo na base de dados.
    assert result is True
    assert repository.deleted_note_id == "nota-123"