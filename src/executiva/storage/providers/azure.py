import mimetypes
from azure.storage.blob import BlobServiceClient, ContentSettings
from executiva.storage.interface import StorageInterface
from executiva.core.config import settings
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError


class AzureStorage(StorageInterface):
    def __init__(self):

        """Cria o cliente Azure a partir da connection string e prepara os contentores privados para documentos, miniaturas e áudio.
        """
        self.blob_service_client = BlobServiceClient.from_connection_string(
            settings.storage_connection_string,
            api_version="2023-11-03"
        )

        self.docs_container = "documentos"
        self.thumbnail_container = "thumbnails"
        self.audio_cache_container = "generated-audio"
        self.library_audio_container = "library-audio"

        self._init_container(self.docs_container)
        self._init_container(self.thumbnail_container)
        self._init_container(self.audio_cache_container)
        self._init_container(self.library_audio_container)

    def save_library_audio(self, blob_name: str, data: bytes) -> None:
        """Envia os bytes MP3 para o contentor privado de áudio guardado na biblioteca, substituindo uma versão anterior com o mesmo nome.
        """
        client = self.blob_service_client.get_container_client(self.library_audio_container).get_blob_client(blob_name)

        client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type="audio/mpeg")
        )

    def get_library_audio(self, blob_name: str) -> bytes | None:
        """Descarrega os bytes do áudio da biblioteca e devolve None quando o blob não existe.
        """
        client = self.blob_service_client.get_container_client(self.library_audio_container).get_blob_client(blob_name)

        try:
            return client.download_blob().readall()
        except ResourceNotFoundError:
            return None

    def delete_library_audio(self, blob_name: str) -> None:
        """Apaga o blob de áudio da biblioteca e ignora o caso em que já não existe.
        """
        client = self.blob_service_client.get_container_client(self.library_audio_container).get_blob_client(blob_name)

        try:
            client.delete_blob()
        except ResourceNotFoundError:
            pass

    def _init_container(self, container_name: str, public_access: str | None = None, ) -> None:
        """Função auxiliar para garantir que o contentor existe e é público"""

        container_client = self.blob_service_client.get_container_client(container_name)

        try:
            container_client.create_container(public_access=public_access)
        except ResourceExistsError:
            # Containers antigos podem ter sido criados como públicos.
            container_client.set_container_access_policy(
                signed_identifiers={},
                public_access=None
            )

    def _get_target_container(self, filename: str) -> str:
        """Lógica de roteamento: se começar por 'thumb_', vai para as miniaturas."""
        if filename.startswith("thumb_"):
            return self.thumbnail_container
        return self.docs_container

    def upload_files_to_storage(self, data: bytes, filename: str) -> str:

        """Envia um documento ou miniatura para o contentor escolhido, define o tipo MIME e devolve o URL do blob.
        """
        container = self._get_target_container(filename)
        container_client = self.blob_service_client.get_container_client(container)

        blob_client = container_client.get_blob_client(blob=filename)

        mime_guess = mimetypes.guess_type(filename)

        content_type = mime_guess[0] if mime_guess and mime_guess[0] else "application/octet-stream"

        settings = ContentSettings(
            content_type=content_type,
            content_disposition="inline"
        )

        blob_client.upload_blob(data, overwrite=True, content_settings=settings)
        return blob_client.url

    def download_files_from_storage(self, filename: str) -> bytes:
        """Descarrega o documento ou miniatura do contentor adequado e devolve os bytes.
        """
        container = self._get_target_container(filename)
        container_client = self.blob_service_client.get_container_client(container)
        blob_client = container_client.get_blob_client(blob=filename)
        return blob_client.download_blob().readall()

    def delete_file_from_storage(self, filename: str):
        """Tenta apagar o documento ou miniatura e regista um aviso se a operação falhar.
        """
        try:
            container = self._get_target_container(filename)
            container_client = self.blob_service_client.get_container_client(container)
            blob_client = container_client.get_blob_client(blob=filename)
            blob_client.delete_blob(delete_snapshots="include")
        except Exception:
            print(f"Aviso do Storage: O ficheiro '{filename}' já não existe no Azurite. Ignorado.")

    def get_cached_audio(self, blob_name: str) -> bytes | None:
        """Lê um MP3 do contentor privado de cache e devolve None se o blob não for encontrado.
        """
        client = self.blob_service_client.get_container_client(
            self.audio_cache_container
        ).get_blob_client(blob_name)

        try:
            return client.download_blob().readall()
        except ResourceNotFoundError:
            return None

    def save_cached_audio(self, blob_name: str, data: bytes) -> None:
        """Grava um MP3 no contentor privado de cache, substituindo o blob com o mesmo nome.
        """
        client = self.blob_service_client.get_container_client(
            self.audio_cache_container
        ).get_blob_client(blob_name)

        client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type="audio/mpeg")

        )

    def delete_cached_audio(self, blob_name: str) -> None:
        """Apaga o MP3 da cache e ignora o caso em que o blob já não existe.
        """
        client = self.blob_service_client.get_container_client(
            self.audio_cache_container
        ).get_blob_client(blob_name)

        try:
            client.delete_blob()
        except ResourceNotFoundError:
            pass

