import os
from pathlib import Path
from executiva.storage.interface import StorageInterface


class LocalStorage(StorageInterface):
    def __init__(self):
        """Define a pasta de ficheiros, a cache de áudio e a biblioteca de áudio. Usa LOCAL_STORAGE_DIR quando configurada e cria as pastas necessárias.
        """
        default_upload_dir = Path(__file__).resolve().parent.parent / "LOCAL_UPLOADS"

        self.upload_dir = Path(
            os.getenv("LOCAL_STORAGE_DIR", str(default_upload_dir))
        ).resolve()

        self.audio_cache_dir = self.upload_dir / ".generated-audio"
        self.library_audio_dir = self.upload_dir / ".library-audio"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.audio_cache_dir.mkdir(parents=True, exist_ok=True)
        self.library_audio_dir.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, directory: Path, filename: str) -> Path:
        """
        Evita que um nome de ficheiro com '..' aceda fora da pasta esperada.
        O contrato atual da interface recebe nomes de ficheiro, não caminhos.
        """
        if not filename or Path(filename).name != filename:
            raise ValueError("O nome do ficheiro não é válido.")

        target_path = (directory / filename).resolve()

        try:
            target_path.relative_to(directory.resolve())
        except ValueError as exc:
            raise ValueError("O caminho do ficheiro não é permitido.") from exc

        return target_path

    def upload_files_to_storage(self, data: bytes, filename: str) -> str:
        """Grava os bytes do documento ou da miniatura no disco local e devolve a referência local usada pela aplicação.
        """
        file_path = self._safe_path(self.upload_dir, filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)

        return f"/local_storage/{filename}"

    def download_files_from_storage(self, filename: str) -> bytes:
        """Lê e devolve os bytes do ficheiro local validando primeiro o caminho.
        """
        file_path = self._safe_path(self.upload_dir, filename)
        return file_path.read_bytes()

    def delete_file_from_storage(self, filename: str):
        """Apaga o documento ou miniatura local se existir; não falha apenas por o ficheiro já ter sido removido.
        """
        file_path = self._safe_path(self.upload_dir, filename)
        if file_path.exists():
            file_path.unlink()

    def get_cached_audio(self, blob_name: str) -> bytes | None:
        """Lê um MP3 da pasta de cache de áudio e devolve None quando ainda não existe.
        """
        audio_path = self._safe_path(self.audio_cache_dir, blob_name)

        if not audio_path.exists():
            return None

        return audio_path.read_bytes()

    def save_cached_audio(self, blob_name: str, data: bytes) -> None:
        """Grava os bytes MP3 na pasta de cache, substituindo o ficheiro com o mesmo nome.
        """
        audio_path = self._safe_path(self.audio_cache_dir, blob_name)
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(data)

    def delete_cached_audio(self, blob_name: str) -> None:
        """Apaga um MP3 da cache se existir.
        """
        audio_path = self._safe_path(self.audio_cache_dir, blob_name)

        if audio_path.exists():
            audio_path.unlink()

    def save_library_audio(self, blob_name: str, data: bytes) -> None:
        """Guarda os bytes MP3 na pasta dedicada aos áudios da biblioteca.
        """
        self._safe_path(self.library_audio_dir, blob_name).write_bytes(data)

    def get_library_audio(self, blob_name: str) -> bytes | None:
        """Lê um áudio guardado na biblioteca ou devolve None se não existir.
        """
        path = self._safe_path(self.library_audio_dir, blob_name)
        return path.read_bytes() if path.exists() else None

    def delete_library_audio(self, blob_name: str) -> None:
        """Remove da pasta da biblioteca o áudio indicado, se estiver presente.
        """
        path = self._safe_path(self.library_audio_dir, blob_name)
        if path.exists():
            path.unlink()
