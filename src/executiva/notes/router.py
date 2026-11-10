from urllib.parse import quote, unquote

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    File,
    Form,
    Query,
    Response,
    UploadFile
)

from executiva.core.dependencies import (
    get_generated_artifact_service,
    get_notes_service,
)
from executiva.academic_structure.loader import load_structure
from executiva.core.security import get_current_user
from executiva.notes.schemas import NotePublic
from executiva.notes.service import NoteService
from executiva.artifacts.service import GeneratedArtifactService
from executiva.notes.processors.pdf_generator import create_acessability_pdf
from executiva.users.models import User

router = APIRouter(prefix="/api/notes", tags=['Notes'] )

def _require_note_exists(note) -> None:
    """Confirma que o apontamento existe e pertence ao utilizador autenticado.
     Interrompe com HTTP 404 ou HTTP 403, respetivamente, se a condição não se verificar.
    """
    if note is None:
        raise HTTPException(
            status_code=404,
            detail="Apontamento não encontrado"
        )

@router.get("/structure")
def get_structure():
    """Devolve a árvore de Escolas, Cursos e Disciplinas (JSON) para desenhar as Dropdowns."""
    return load_structure()

@router.get("/", response_model=list[NotePublic])
def list_notes(
    school:str | None=None,
    course:str | None=None,
    year:str | None=None,
    subject:str | None=None,
    service: NoteService = Depends(get_notes_service)
):
    """Devolve os apontamentos que correspondem aos filtros académicos recebidos como parâmetros de consulta.
    """
    return service.get_filtered_notes(school, course, year, subject)

@router.post("/upload")
def upload_file(
    title: str = Form(...),
    school: str = Form(...),
    course: str = Form(...),
    year: str = Form(...),
    subject: str = Form(...),
    file: UploadFile = File(...),
    service: NoteService = Depends(get_notes_service),
    current_user: User = Depends(get_current_user)
):
    """Recebe os campos do formulário e o ficheiro enviado, exige autenticação e delega a validação, armazenamento e persistência ao serviço de apontamentos.
    """
    service.process_upload(title, school, course, year, subject, file, current_user.email)
    return {"message": "Upload completo!"}


@router.get("/me", response_model=list[NotePublic])
def list_my_notes(service: NoteService = Depends(get_notes_service),
                  current_user: User = Depends(get_current_user)):
    """Devolve apenas os apontamentos de quem fez o login"""
    return service.get_my_notes(current_user.email, current_user.id)


@router.get("/{note_id}")
def get_note_details(
        note_id: str, service: NoteService = Depends(get_notes_service)
):
    """Ver os detalhes e metadados de um apontamento."""
    note = service.get_note_by_id(note_id)
    if note is None:
        raise HTTPException(
            status_code=404,
            detail="Não encontrado"
        )
    return {
        "id": note.id,
        "title": note.title,
        "school": note.school,
        "course": note.course,
        "year": note.year,
        "subject": note.subject,
        "author": note.author,
        "file_url": f"/api/notes/{note.id}/view",
        "thumbnail_url": (
            f"/api/notes/{note.id}/thumbnail"
            if note.thumbnail_url
            else None
        )
    }


@router.get("/{note_id}/read")
def read_note(
        note_id: str,
        service: NoteService = Depends(get_notes_service),
        _current_user: User = Depends(get_current_user)
):
    """Exige que o utilizador seja o autor, extrai o conteúdo textual do ficheiro e devolve os metadados juntamente com o texto.
    """
    _require_note_exists(service.get_note_by_id(note_id))
    note_data = service.read_note_content(note_id)
    if note_data is None:
        raise HTTPException(
            status_code=404,
            detail="Não encontrado"
        )
    return note_data


@router.get("/{note_id}/view")
def view_note_file(
        note_id: str,
        service: NoteService = Depends(get_notes_service),
        _current_user: User = Depends(get_current_user),
):
    """Verifica a propriedade do apontamento, descarrega o ficheiro original e devolve-o inline com o tipo MIME correspondente a PDF ou DOCX.
    """
    _require_note_exists(service.get_note_by_id(note_id))
    data = service.prepare_download(note_id)

    if data is None:
        raise HTTPException(
            status_code=404,
            detail="Não encontrado"
        )
    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if data["filename"].lower().endswith(".docx")
        else "application/pdf"
    )
    return Response(
        content=data["bytes"],
        media_type=media_type,
        headers={"Content-Disposition": "inline"}
    )


@router.get("/{note_id}/thumbnail")
def view_note_thumbnail(
        note_id: str,
        service: NoteService = Depends(get_notes_service),
        _current_user: User = Depends(get_current_user),
):
    """Verifica a propriedade do apontamento e devolve a miniatura PNG através da API, sem tornar público o URL do blob.
    """
    note = service.get_note_by_id(note_id)
    _require_note_exists(note)
    if not note.thumbnail_url:
        raise HTTPException(status_code=404, detail="Miniatura não encontrada")
    filename = unquote(note.thumbnail_url.rsplit("/", 1)[-1])
    try:
        data = service.storage.download_files_from_storage(filename)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail="Miniatura não encontrada"
        ) from exc
    return Response(
        content=data,
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=3600"}
    )


@router.get("/{note_id}/download")
def download_note_file(
        note_id: str,
        service: NoteService = Depends(get_notes_service),
        _current_user: User = Depends(get_current_user)
):
    """Verifica a propriedade do apontamento e envia o documento como anexo, com um nome de ficheiro codificado para o cabeçalho HTTP.
    """
    _require_note_exists(service.get_note_by_id(note_id))
    """Vai buscar o ficheiro à Cloud e injeta-o na resposta como um anexo transferível."""
    data = service.prepare_download(note_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Ficheiro não encontrado")

    # O FastAPI Response devolve os bytes diretamente para o browser fazer download

    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if data["filename"].lower().endswith(".docx")
        else "application/pdf"
    )
    return Response(
        content=data["bytes"],
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{quote(data['filename'])}"
            )
        }
    )


@router.delete("/{note_id}")
def delete_note(
        note_id: str,
        service: NoteService = Depends(get_notes_service),
        current_user: User = Depends(get_current_user)
):
    """Apaga da BD e apaga os blobs da Cloud se pertencer ao utilizador."""
    service.delete_note(note_id, current_user.email)
    return {"message": "Apontamento apagado com sucesso"}


@router.get("/{note_id}/adapt")
def adapt_note(
        note_id: str,
        service: NoteService = Depends(get_notes_service),
        _current_user: User = Depends(get_current_user),
        artifacts: GeneratedArtifactService = Depends(get_generated_artifact_service)
):
    """Extrai o texto do ficheiro e envia para a IA formatar."""
    _require_note_exists(service.get_note_by_id(note_id))
    note_data = service.read_note_content(note_id)

    if note_data is None or not note_data['content']:
        raise HTTPException(
            status_code=404,
            detail="Não foi possível extrair texto do apontamento."
        )

    summary, _ = artifacts.get_or_create_summary(
        note_id,
        note_data['content']
    )

    pdf_bytes = create_acessability_pdf(note_data["title"], summary)

    return Response(content=pdf_bytes, media_type="application/pdf")


@router.get("/{note_id}/audio")
async def get_note_audio(
        note_id: str,
        audio_type: str = Query("original", pattern="^(original|adapted)$"),
        service: NoteService = Depends(get_notes_service),
        current_user: User = Depends(get_current_user),
        artifacts: GeneratedArtifactService = Depends(get_generated_artifact_service)
):
    """Verifica a propriedade e gera ou reutiliza áudio do texto original ou do resumo adaptado, consoante o parâmetro type.
    """
    _require_note_exists(service.get_note_by_id(note_id))
    note_data = service.read_note_content(note_id)
    if note_data is None or not note_data['content']:
        raise HTTPException(
            status_code=404,
            detail="Apontamento não encontrado"
        )

    if audio_type == "adapted":
        text_to_read, _ = artifacts.get_or_create_summary(note_id, note_data['content'])
    else:
        text_to_read = note_data["content"]

    audio_bytes, _ = await artifacts.get_or_create_audio(
        note_id=note_id,
        variant=audio_type,
        text=text_to_read
    )
    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.post("/{note_id}/like")
def like_note(
        note_id: str,
        current_user: User = Depends(get_current_user),
        service: NoteService = Depends(get_notes_service)
):
    """Regista o gosto do utilizador e devolve a contagem atual."""
    return service.like_note(note_id, current_user.id)


@router.delete("/{note_id}/like")
def delete_like(
        note_id: str,
        current_user: User = Depends(get_current_user),
        service:NoteService = Depends(get_notes_service)
):
    """Remove o gosto do utilizador e devolve a contagem atual."""
    return service.delete_like(note_id, current_user.id)