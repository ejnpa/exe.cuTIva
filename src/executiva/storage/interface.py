from abc import ABC, abstractmethod


class StorageInterface(ABC):
    """Define as operações comuns dos fornecedores de armazenamento."""

    @abstractmethod
    def upload_files_to_storage(self, data: bytes, filename: str) -> str:
        """Guarda um documento ou miniatura e devolve uma referência."""
        raise NotImplementedError

    @abstractmethod
    def download_files_from_storage(self, filename: str) -> bytes:
        """Lê um documento ou miniatura."""
        raise NotImplementedError

    @abstractmethod
    def delete_file_from_storage(self, filename: str):
        """Apaga um documento ou miniatura."""
        raise NotImplementedError

    @abstractmethod
    def get_cached_audio(self, blob_name: str) -> bytes | None:
        """Lê áudio da cache; devolve None se não existir."""
        raise NotImplementedError

    @abstractmethod
    def save_cached_audio(self, blob_name: str, data: bytes):
        """Guarda áudio na cache."""
        raise NotImplementedError

    @abstractmethod
    def delete_cached_audio(self, blob_name: str) -> None:
        """Apaga áudio da cache."""
        raise NotImplementedError

    @abstractmethod
    def save_library_audio(self, blob_name: str, data: bytes) -> None:
        """Define a gravação persistente de áudio associado à biblioteca do utilizador.
        """
        raise NotImplementedError

    @abstractmethod
    def get_library_audio(self, blob_name: str) -> bytes | None:
        """Define a leitura de áudio guardado na biblioteca, devolvendo None se não existir.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_library_audio(self, blob_name: str) -> None:
        """Define a remoção de áudio guardado na biblioteca.
        """
        raise NotImplementedError
