from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile

from executiva.notes.service import NoteService


class FakeRepository:
    def __init__(self, note=None, create_error=None):
        self.note = note
        self.create_error = create_error
        self.created_data = None
        self.deleted_note_id = None

    def create(self, note_data):
        self.created_data = note_data
        if self.create_error:
            raise self.create_error
        self.note = SimpleNamespace(**note_data)
        return self.note

    def get_by_id(self, note_id):
        if self.note and self.note.id == note_id:
            return self.note
        return None

    def delete_note(self, note_id):
        self.deleted_note_id = note_id
        self.note = None


class FakeStorage:
    def __init__(self, download_error=None, delete_error=None):
        self.download_error = download_error
        self.delete_error = delete_error
        self.uploads = []
        self.downloads = []
        self.deletes = []

    def upload_files_to_storage(self, data, filename):
        self.uploads.append((data, filename))
        return f"https://storage.test/{filename}"

    def download_files_from_storage(self, filename):
        self.downloads.append(filename)
        if self.download_error:
            raise self.download_error
        return b"conteudo"

    def delete_file_from_storage(self, filename):
        self.deletes.append(filename)
        if self.delete_error:
            raise self.delete_error


def make_note(**overrides):
    values = {
        "id": "nota-1",
        "title": "Nota",
        "school": "Escola",
        "course": "Curso",
        "year": "1",
        "subject": "Programação",
        "author": "ana@example.pt",
        "file_url": "https://storage.test/uuid_documento%20final.pdf",
        "thumbnail_url": "https://storage.test/thumb_uuid_documento.png",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_upload(filename, data):
    return UploadFile(filename=filename, file=BytesIO(data))


def make_service(repository=None, storage=None):
    return NoteService(
        repo=repository or FakeRepository(),
        storage=storage or FakeStorage(),
    )


@pytest.mark.parametrize(
    ("filename", "data", "status"),
    [
        ("nota.txt", b"texto", 415),
        ("nota.pdf", b"", 400),
        ("nota.pdf", b"nao e um pdf", 400),
    ],
)
def test_upload_rejeita_formato_ou_conteudo_invalido(
    filename,
    data,
    status,
    monkeypatch,
):
    monkeypatch.setattr(
        "executiva.notes.service.generate_pdf_thumbnail_bytes",
        lambda *args: None,
    )
    storage = FakeStorage()
    service = make_service(storage=storage)

    with pytest.raises(HTTPException) as error:
        service.process_upload(
            "Nota", "Escola", "Curso", "1", "Disciplina",
            make_upload(filename, data), "ana@example.pt",
        )

    assert error.value.status_code == status
    assert storage.uploads == []


def test_upload_rejeita_ficheiro_acima_do_limite(monkeypatch):
    monkeypatch.setattr(
        "executiva.notes.service.settings.max_upload_size_bytes",
        4,
    )
    storage = FakeStorage()
    service = make_service(storage=storage)

    with pytest.raises(HTTPException) as error:
        service.process_upload(
            "Nota", "Escola", "Curso", "1", "Disciplina",
            make_upload("nota.pdf", b"%PDF-123"), "ana@example.pt",
        )

    assert error.value.status_code == 413
    assert storage.uploads == []


def test_upload_guarda_pdf_e_miniatura(monkeypatch):
    monkeypatch.setattr(
        "executiva.notes.service.generate_pdf_thumbnail_bytes",
        lambda data, filename: b"miniatura-png",
    )
    repository = FakeRepository()
    storage = FakeStorage()
    service = make_service(repository=repository, storage=storage)

    result = service.process_upload(
        "Nota", "Escola", "Curso", "1", "Disciplina",
        make_upload(r"C:\tmp\documento de teste.pdf", b"%PDF-1.7 dados"),
        "ana@example.pt",
    )

    assert result is repository.note
    assert len(storage.uploads) == 2
    assert storage.uploads[0][0] == b"%PDF-1.7 dados"
    assert storage.uploads[0][1].endswith("_documento_de_teste.pdf")
    assert storage.uploads[1][0] == b"miniatura-png"
    assert storage.uploads[1][1].startswith("thumb_")
    assert repository.created_data["author"] == "ana@example.pt"


def test_upload_remove_ficheiros_se_a_persistencia_falhar(monkeypatch):
    monkeypatch.setattr(
        "executiva.notes.service.generate_pdf_thumbnail_bytes",
        lambda data, filename: b"miniatura-png",
    )
    repository = FakeRepository(create_error=RuntimeError("BD indisponível"))
    storage = FakeStorage()
    service = make_service(repository=repository, storage=storage)

    with pytest.raises(RuntimeError, match="BD indisponível"):
        service.process_upload(
            "Nota", "Escola", "Curso", "1", "Disciplina",
            make_upload("nota.pdf", b"%PDF-1.7 dados"),
            "ana@example.pt",
        )

    uploaded_names = [filename for _, filename in storage.uploads]
    assert storage.deletes == uploaded_names


def test_read_content_devolve_none_para_nota_inexistente():
    service = make_service()

    assert service.read_note_content("ausente") is None


def test_read_content_rejeita_nota_sem_ficheiro():
    service = make_service(repository=FakeRepository(make_note(file_url=None)))

    with pytest.raises(HTTPException) as error:
        service.read_note_content("nota-1")

    assert error.value.status_code == 404


def test_read_content_mapeia_falha_de_storage_para_404():
    service = make_service(
        repository=FakeRepository(make_note()),
        storage=FakeStorage(download_error=OSError("blob ausente")),
    )

    with pytest.raises(HTTPException) as error:
        service.read_note_content("nota-1")

    assert error.value.status_code == 404


def test_read_content_decodifica_nome_de_ficheiro_url():
    storage = FakeStorage()
    service = make_service(
        repository=FakeRepository(make_note()),
        storage=storage,
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        "executiva.notes.service.extract_text_from_file",
        lambda data, filename: filename,
    )

    try:
        result = service.read_note_content("nota-1")
    finally:
        monkeypatch.undo()

    assert storage.downloads == ["uuid_documento final.pdf"]
    assert result["content"] == "uuid_documento final.pdf"


def test_prepare_download_lida_com_nota_sem_ficheiro_e_storage_indisponivel():
    service = make_service(repository=FakeRepository(make_note(file_url=None)))
    assert service.prepare_download("nota-1") is None

    service = make_service(
        repository=FakeRepository(make_note()),
        storage=FakeStorage(download_error=OSError("indisponível")),
    )
    with pytest.raises(HTTPException) as error:
        service.prepare_download("nota-1")
    assert error.value.status_code == 404


def test_prepare_download_decodifica_nome_original():
    service = make_service(
        repository=FakeRepository(make_note()),
        storage=FakeStorage(),
    )

    result = service.prepare_download("nota-1")

    assert result == {
        "bytes": b"conteudo",
        "filename": "documento final.pdf",
    }
