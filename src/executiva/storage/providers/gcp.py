import mimetypes
import os
from google.api_core.exceptions import NotFound
from google.cloud import storage
from executiva.storage.interface import StorageInterface


class GCPStorage(StorageInterface):
    def __init__(self):
        """Lê o nome do bucket GCP, cria o cliente e define os prefixos usados para documentos, miniaturas e áudio. Falha se o bucket não estiver configurado.
        """
        self.bucket_name = os.getenv("GCP_STORAGE_BUCKET")
        if not self.bucket_name:
            raise RuntimeError("Define a variável de ambiente GCP_STORAGE_BUCKET.")

        self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)

        self.docs_prefix = "documentos"
        self.thumbnail_prefix = "thumbnails"
        self.audio_cache_prefix = "generated-audio"
        self.library_audio_prefix = "library-audio"

    def _get_file_blob_name(self, filename: str) -> str:
        """Valida um nome simples de ficheiro e acrescenta o prefixo de documentos ou miniaturas adequado.
        """
        if not filename or "/" in filename or "\\" in filename:
            raise ValueError("O nome do ficheiro não é válido.")

        prefix = (
            self.thumbnail_prefix if filename.startswith("thumb_") else self.docs_prefix
        )

        return f"{prefix}/{filename}"

    def _get_audio_blob_name(self, blob_name: str) -> str:
        """Valida o nome simples do áudio e acrescenta o prefixo da cache de áudio, evitando separadores de caminho.
        """
        if not blob_name or "/" in blob_name or "\\" in blob_name:
            raise ValueError("O nome do audio não é válido.")

        if ".." in blob_name.split("/"):
            raise ValueError("O caminho do áudio não é permitido.")

        return f"{self.audio_cache_prefix}/{blob_name}"

    def upload_files_to_storage(self, data: bytes, filename: str) -> str:
        """Envia os bytes para o bucket com o tipo MIME inferido pelo nome e devolve o URL público do blob.
        """
        blob_name = self._get_file_blob_name(filename)
        blob = self.bucket.blob(blob_name)

        mime_type, _ = mimetypes.guess_type(filename)
        blob.upload_from_string(data, content_type=mime_type or "application/octet-stream")
        return blob.public_url

    def download_files_from_storage(self, filename: str) -> bytes:
        """Descarrega e devolve os bytes do documento ou miniatura do bucket.
        """
        blob_name = self._get_file_blob_name(filename)
        blob = self.bucket.blob(blob_name)
        return blob.download_as_bytes()

    def delete_file_from_storage(self, filename: str):
        """Apaga um documento ou miniatura do bucket; ignora o caso em que o blob já não existe.
        """
        blob_name = self._get_file_blob_name(filename)
        blob = self.bucket.blob(blob_name)

        try:
            blob.delete()
        except NotFound:
            pass

    def get_cached_audio(self, blob_name: str) -> bytes | None:
        """Obtém os bytes de áudio da cache e devolve None se o blob não existir.
        """
        full_blob_name = self._get_audio_blob_name(blob_name)
        blob = self.bucket.blob(full_blob_name)

        try:
            return blob.download_as_bytes()
        except NotFound:
            return None

    def save_cached_audio(self, blob_name: str, data: bytes) -> None:
        """Envia um MP3 para o prefixo de cache de áudio do bucket.
        """
        full_blob_name = self._get_audio_blob_name(blob_name)
        blob = self.bucket.blob(full_blob_name)

        blob.upload_from_string(data, content_type="audio/mpeg")

    def delete_cached_audio(self, blob_name: str) -> None:
        """Apaga um MP3 da cache, ignorando a resposta de blob inexistente.
        """
        full_blob_name = self._get_audio_blob_name(blob_name)
        blob = self.bucket.blob(full_blob_name)

        try:
            blob.delete()
        except NotFound:
            pass

    def save_library_audio(self, blob_name: str, data: bytes) -> None:
        """Guarda um MP3 no prefixo reservado aos áudios da biblioteca.
        """
        if not blob_name or "/" in blob_name or "\\" in blob_name:
            raise ValueError("O nome do áudio não é válido.")
        self.bucket.blob(f"{self.library_audio_prefix}/{blob_name}").upload_from_string(data, content_type="audio/mpeg")

    def get_library_audio(self, blob_name: str) -> bytes | None:
        """Descarrega um áudio guardado na biblioteca ou devolve None se não existir.
        """
        if not blob_name or "/" in blob_name or "\\" in blob_name:
            raise ValueError("O nome do áudio não é válido.")
        blob = self.bucket.blob(f"{self.library_audio_prefix}/{blob_name}")
        try:
            return blob.download_as_bytes()
        except NotFound:
            return None

    def delete_library_audio(self, blob_name: str) -> None:
        """Apaga um áudio da biblioteca, sem falhar se já tiver sido removido.
        """
        if not blob_name or "/" in blob_name or "\\" in blob_name:
            raise ValueError("O nome do áudio não é válido.")
        try:
            self.bucket.blob(f"{self.library_audio_prefix}/{blob_name}").delete()
        except NotFound:
            pass
