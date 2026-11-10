from types import SimpleNamespace

import pytest
from azure.core.exceptions import ResourceNotFoundError
from google.api_core.exceptions import NotFound

from executiva.storage.factory import get_storage_provider
from executiva.storage.interface import StorageInterface
from executiva.storage.providers import azure, gcp
from executiva.storage.providers.local import LocalStorage


def test_storage_factory_seleciona_fornecedor_local(monkeypatch):
    class FakeLocalStorage:
        pass

    monkeypatch.setenv("CLOUD_PROVIDER", "local")
    monkeypatch.setattr("executiva.storage.factory.LocalStorage", FakeLocalStorage)

    assert isinstance(get_storage_provider(), FakeLocalStorage)


def test_storage_factory_rejeita_fornecedor_desconhecido(monkeypatch):
    monkeypatch.setenv("CLOUD_PROVIDER", "desconhecido")

    with pytest.raises(ValueError, match="CLOUD_PROVIDER inválido"):
        get_storage_provider()


def test_local_storage_guarda_le_e_apaga_ficheiros(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_STORAGE_DIR", str(tmp_path / "uploads"))
    storage = LocalStorage()

    url = storage.upload_files_to_storage(b"conteudo", "documento.pdf")

    assert url == "/local_storage/documento.pdf"
    assert storage.download_files_from_storage("documento.pdf") == b"conteudo"
    storage.delete_file_from_storage("documento.pdf")
    storage.delete_file_from_storage("documento.pdf")
    assert not (tmp_path / "uploads" / "documento.pdf").exists()


@pytest.mark.parametrize("filename", ["", "../fora.txt", "..\\fora.txt", "sub/pasta.txt"])
def test_local_storage_rejeita_caminhos(filename, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_STORAGE_DIR", str(tmp_path))
    storage = LocalStorage()

    with pytest.raises(ValueError):
        storage.upload_files_to_storage(b"x", filename)


def test_local_storage_cache_e_biblioteca_audio(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_STORAGE_DIR", str(tmp_path))
    storage = LocalStorage()

    assert storage.get_cached_audio("cache.mp3") is None
    storage.save_cached_audio("cache.mp3", b"cache")
    assert storage.get_cached_audio("cache.mp3") == b"cache"
    storage.delete_cached_audio("cache.mp3")
    storage.delete_cached_audio("cache.mp3")

    assert storage.get_library_audio("biblioteca.mp3") is None
    storage.save_library_audio("biblioteca.mp3", b"biblioteca")
    assert storage.get_library_audio("biblioteca.mp3") == b"biblioteca"
    storage.delete_library_audio("biblioteca.mp3")
    assert storage.get_library_audio("biblioteca.mp3") is None


def test_local_storage_rejeita_traversal_na_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_STORAGE_DIR", str(tmp_path))
    storage = LocalStorage()

    with pytest.raises(ValueError):
        storage.get_cached_audio("..\\fora.mp3")


class FakeBlob:
    def __init__(self, name):
        self.name = name
        self.url = f"https://storage.example/{name}"
        self.public_url = f"https://storage.example/{name}"
        self.uploads = []
        self.data = None
        self.deleted = False

    def upload_blob(self, data, **kwargs):
        self.data = data
        self.uploads.append(kwargs)

    def upload_from_string(self, data, **kwargs):
        self.data = data
        self.uploads.append(kwargs)

    def download_blob(self):
        if self.data is None:
            raise ResourceNotFoundError("not found")
        return SimpleNamespace(readall=lambda: self.data)

    def download_as_bytes(self):
        if self.data is None:
            raise NotFound("not found")
        return self.data

    def delete_blob(self, **kwargs):
        self.deleted = True
        self.data = None

    def delete(self):
        self.deleted = True
        self.data = None


class FakeContainer:
    def __init__(self, name):
        self.name = name
        self.blobs = {}
        self.created_with = None
        self.access_policy = None

    def create_container(self, **kwargs):
        self.created_with = kwargs

    def set_container_access_policy(self, **kwargs):
        self.access_policy = kwargs

    def get_blob_client(self, blob):
        return self.blobs.setdefault(blob, FakeBlob(blob))

    def blob(self, name):
        return self.blobs.setdefault(name, FakeBlob(name))


class FakeBlobService:
    def __init__(self):
        self.containers = {}

    def get_container_client(self, name):
        return self.containers.setdefault(name, FakeContainer(name))


def test_azure_storage_encaminha_documento_e_thumbnail(monkeypatch):
    fake_service = FakeBlobService()
    monkeypatch.setattr(
        azure.BlobServiceClient,
        "from_connection_string",
        lambda *args, **kwargs: fake_service,
    )
    storage = azure.AzureStorage()

    document_url = storage.upload_files_to_storage(b"pdf", "nota.pdf")
    thumbnail_url = storage.upload_files_to_storage(b"png", "thumb_nota.png")

    assert document_url.endswith("nota.pdf")
    assert thumbnail_url.endswith("thumb_nota.png")
    assert fake_service.containers["documentos"].blobs["nota.pdf"].data == b"pdf"
    assert fake_service.containers["thumbnails"].blobs["thumb_nota.png"].data == b"png"


def test_azure_storage_guarda_e_le_audio_da_biblioteca(monkeypatch):
    fake_service = FakeBlobService()
    monkeypatch.setattr(
        azure.BlobServiceClient,
        "from_connection_string",
        lambda *args, **kwargs: fake_service,
    )
    storage = azure.AzureStorage()

    storage.save_library_audio("a.mp3", b"audio")

    assert storage.get_library_audio("a.mp3") == b"audio"
    storage.delete_library_audio("a.mp3")
    assert storage.get_library_audio("a.mp3") is None


class FakeGCPBucket:
    def __init__(self):
        self.blobs = {}

    def blob(self, name):
        return self.blobs.setdefault(name, FakeBlob(name))


class FakeGCPClient:
    def __init__(self):
        self.fake_bucket = FakeGCPBucket()

    def bucket(self, name):
        assert name == "test-bucket"
        return self.fake_bucket


def test_gcp_storage_exige_nome_de_bucket(monkeypatch):
    monkeypatch.delenv("GCP_STORAGE_BUCKET", raising=False)

    with pytest.raises(RuntimeError, match="GCP_STORAGE_BUCKET"):
        gcp.GCPStorage()


def test_gcp_storage_encaminha_ficheiros_e_audio(monkeypatch):
    fake_client = FakeGCPClient()
    monkeypatch.setenv("GCP_STORAGE_BUCKET", "test-bucket")
    monkeypatch.setattr(gcp.storage, "Client", lambda: fake_client)
    storage = gcp.GCPStorage()

    url = storage.upload_files_to_storage(b"pdf", "nota.pdf")
    storage.save_cached_audio("cache.mp3", b"audio-cache")
    storage.save_library_audio("saved.mp3", b"audio-saved")

    assert url.endswith("documentos/nota.pdf")
    assert storage.download_files_from_storage("nota.pdf") == b"pdf"
    assert storage.get_cached_audio("cache.mp3") == b"audio-cache"
    assert storage.get_library_audio("saved.mp3") == b"audio-saved"
    assert fake_client.fake_bucket.blobs[
        "generated-audio/cache.mp3"
    ].uploads[0]["content_type"] == "audio/mpeg"


@pytest.mark.parametrize("filename", ["", "../escape", "a/b", "a\\b"])
def test_gcp_storage_rejeita_nomes_de_ficheiro_invalidos(
    filename,
    monkeypatch,
):
    monkeypatch.setenv("GCP_STORAGE_BUCKET", "test-bucket")
    monkeypatch.setattr(gcp.storage, "Client", FakeGCPClient)
    storage = gcp.GCPStorage()

    with pytest.raises(ValueError):
        storage.download_files_from_storage(filename)


def test_interface_storage_nao_pode_ser_instanciada_diretamente():
    with pytest.raises(TypeError):
        StorageInterface()
