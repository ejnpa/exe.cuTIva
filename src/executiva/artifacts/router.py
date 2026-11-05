

from fastapi import APIRouter, Depends, HTTPException


from executiva.core.dependencies import (
    get_notes_service,
    get_generated_artifact_service
)
from executiva.core.security import get_current_user
from executiva.artifacts.service import GeneratedArtifactService
from executiva.notes.service import NoteService
from executiva.users.models import User
from executiva.artifacts.schemas import SavedArtifactRequest,SavedArtifactResponse

router = APIRouter(prefix="/api/library", tags=['Library'])




@router.post("/save")
async def save_artifact(
        request: SavedArtifactRequest,
        current_user: User = Depends(get_current_user),
        notes: NoteService = Depends(get_notes_service),
        artifacts: GeneratedArtifactService = Depends(get_generated_artifact_service)
):
    """Gera ou reutiliza o artefacto e guarda-o na biblioteca do utilizador."""
    note = notes.get_note_by_id(request.note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Apontamento não encontrado")
    if note.author != current_user.email:
        raise HTTPException(
            status_code=403,
            detail="Não tem permissão para guardar artefactos deste apontamento"
        )
    note_data = notes.read_note_content(request.note_id)
    if note_data is None or not note_data.get("content"):
        raise HTTPException(
            status_code=404,
            detail="Não foi possível obter o conteúdo do apontamento"
        )
    try:
        if request.kind == 'summary':
            _, cache_key = artifacts.get_or_create_summary(
                request.note_id,
                note_data["content"]
            )
        else:
            text_to_read = note_data["content"]
            if request.variant == "adapted":
                text_to_read, _ = artifacts.get_or_create_summary(
                    request.note_id,
                    note_data["content"]
                )

            _, cache_key = await artifacts.get_or_create_audio(
                request.note_id,
                request.variant,
                text_to_read
            )
        artifacts.cache.pin(current_user.id, cache_key)
    except ValueError as exc:
        raise HTTPException( status_code= 404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException( status_code= 502, detail=str(exc)) from exc
    return SavedArtifactResponse(message="Guardado na Biblioteca")
