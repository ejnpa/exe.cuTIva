from fastapi import Depends
from sqlalchemy.orm import Session

from executiva.artifacts.cache_repository import GeneratedCacheRepository
from executiva.artifacts.service import GeneratedArtifactService
from executiva.audio.service import AudioService
from executiva.core.config import settings
from executiva.db.session import get_db
from executiva.notes.repository import NotesRepository
from executiva.notes.service import NoteService
from executiva.ai.service import AIAccessibilityService
from executiva.storage.factory import get_storage_provider



def get_notes_service(
    db: Session = Depends(get_db)
) -> NoteService:
    "Cria o serviço de apontamentos com acesso à base de dados e ao armazenamento."""
    repository = NotesRepository(db)
    storage = get_storage_provider()
    return NoteService(
        repo=repository,
        storage=storage
    )

def get_generated_artifact_service(
        db: Session = Depends(get_db)
) -> GeneratedArtifactService:
    """Cria o serviço de artefactos com acesso à base de dados e ao armazenamento."""
    ttl_days = settings.generated_cache_ttl_days
    cache = GeneratedCacheRepository(
        db =db,
        ttl_days = ttl_days
    )

    return GeneratedArtifactService(
        cache=cache,
        storage = get_storage_provider(),
        ai_service = AIAccessibilityService(),
        audio_service = AudioService(),
        ttl_days= ttl_days
    )

