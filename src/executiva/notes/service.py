
import uuid

from pathlib import Path
from urllib.parse import unquote

from fastapi import HTTPException, UploadFile

from executiva.core.config import settings
from executiva.notes.processors.image_extractor import generate_pdf_thumbnail_bytes
from executiva.notes.processors.text_extractor import extract_text_from_file
from executiva.notes.repository import NotesRepository

class NoteService:
    def __init__(self, repo: NotesRepository, storage):
        """Recebe o repositório de apontamentos e o fornecedor de armazenamento, que serão usados nas operações deste serviço.
        """
        self.repo = repo
        self.storage = storage

    def process_upload(self, title: str,
                       school: str,
                       course: str,
                       year: str,
                       subject: str,
                       file: UploadFile,
                       author_email: str):
        """Valida extensão, tamanho e estrutura básica do PDF ou DOCX; gera um identificador único, guarda o documento e, quando possível, uma miniatura, e cria o registo na base de dados. Se a criação do registo falhar, tenta remover os ficheiros já enviados.
        """
        original_name = (file.filename or "upload").replace("\\","/").split("/")[-1]
        extension = Path(original_name).suffix.lower()

        if extension not in {".pdf", ".png"}:
            raise HTTPException(
                status_code=415,
                detail="Formato não suportado."
            )

        file_bytes = file.file.read(settings.max_upload_size_bytes + 1)

        if len(file_bytes) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=413,
                detail="O ficheiro excede o limite."
            )
        if not file_bytes:
            raise HTTPException(status_code=400, detail="O ficheiro está vazio.")

        if extension == ".pdf" and file_bytes.find(b"%PDF-") not in range(1024):
            raise HTTPException(
                status_code=400,
                detail="O conteúdo não corresponde a um PDF válido."
            )

        new_id = str(uuid.uuid4())
        safe_filename = f"{new_id}_{original_name.replace(' ', '_')}"


        file_url = self.storage.upload_files_to_storage(
            file_bytes,
            safe_filename
        )
        thumbnail_url = None
        thumbnail_name = None
        thumb_bytes = generate_pdf_thumbnail_bytes(
            file_bytes,
            safe_filename
        )

        if thumb_bytes:
            thumb_filename = f"thumb_{safe_filename}.png"
            thumbnail_url = self.storage.upload_files_to_storage(
                thumb_bytes,
                thumb_filename
            )

        note_data = {
            "id": new_id,
            "title": title,
            "school": school,
            "course": course,
            "year": year,
            "subject": subject,
            "author": author_email,
            "file_url": file_url,
            "thumbnail_url": thumbnail_url
        }

        try:
            return self.repo.create(note_data)
        except Exception:
            # Evita deixar ficheiros órfãos se a gravação da base de dados falhar.
            for stored_name in (safe_filename, thumbnail_name):
                if stored_name:
                    try:
                        self.storage.delete_file_from_storage(stored_name)
                    except Exception:
                        pass
            raise

    def read_note_content(self, note_id: str) -> dict | None:
        """Obtém o apontamento, descarrega o ficheiro do armazenamento e extrai o texto. Devolve metadados e conteúdo extraído, None se o apontamento não existir e HTTP 404 se o ficheiro físico não puder ser descarregado.
        """
        note = self.repo.get_by_id(note_id)
        if note is None:
            return None

        if not note.file_url:
            raise HTTPException(
                status_code=404,
                detail="O apontamento não tem ficheiro associado."
            )
        filename = unquote(note.file_url.split("/")[-1])
        try:
            file_bytes = self.storage.download_files_from_storage(filename)
        except Exception as exc:
            raise HTTPException(
                status_code=404,
                detail="O ficheiro físico já não existe no servidor."
            ) from exc

        return {
            "id": note.id,
            "title": note.title,
            "subject": note.subject,
            "author": note.author,
            "file_url": f"/api/notes/{note.id}/view",
            "thumbnail_url":( f"/api/notes/{note.id}/thumbnail"
                             if note.thumbnail_url
                                else None),
            "content": extract_text_from_file(file_bytes, filename)
        }

    def get_filtered_notes(
            self,
            school: str| None = None,
            course: str | None = None,
            year: str | None= None,
            subject: str | None= None
    ) -> list[dict]:
        """Encaminha os filtros académicos para o repositório e devolve os apontamentos correspondentes.
        """
        return self.repo.get_all_with_filters(
            school = school,
            course = course,
            year = year,
            subject = subject
        )

    def get_my_notes(self, author_email: str, current_user_id: int) -> list[dict]:
        """Devolve os apontamentos do email do utilizador atual, incluindo o estado dos gostos desse utilizador.
        """
        return self.repo.get_by_author(author_email, current_user_id)

    def get_note_by_id(self, note_id: str):
        """Delega no repositório a procura de um apontamento pelo identificador.
        """
        return self.repo.get_by_id(note_id)

    def prepare_download(self, note_id: str) -> dict | None:
        """Obtém os bytes do ficheiro original e determina o nome a apresentar ao navegador. Devolve None se o registo não existir.
        """
        note = self.repo.get_by_id(note_id)
        if note is None or not note.file_url:
            return None

        stored_name = unquote(note.file_url.split("/")[-1])
        try:
            file_bytes = self.storage.download_files_from_storage(stored_name)
        except Exception as exc:
            raise HTTPException(status_code=404, detail="Ficheiro não encontrado.",
                                )from exc

        original_name = stored_name.split("_", 1)[-1]
        return {"bytes": file_bytes, "filename": original_name}

    def delete_note(self, note_id: str, current_user_email: str) -> bool:
        """Apaga o apontamento e os ficheiros associados após confirmar a autoria.

        Devolve HTTP 404 se o registo não existir e HTTP 403 se pertencer a outro
        utilizador. Erros ao remover ficheiros físicos são registados como aviso;
        a remoção do registo da base de dados prossegue para evitar referências
        inválidas a ficheiros que já não possam ser recuperados.
        """
        note = self.repo.get_by_id(note_id)
        if note is None:
            raise HTTPException(
                status_code=404,
                detail="Apontamento não encontrado"
            )

        if note.author != current_user_email:
            raise HTTPException(
                status_code=403,
                detail="Não tem permissão para efetuar esta ação"
            )
        stored_names =[]
        if note.file_url:
            stored_names.append(unquote(note.file_url.rsplit("/", 1)[1]))
        if note.thumbnail_url:
            stored_names.append(unquote(note.thumbnail_url.rsplit("/", 1)[1]))

        for stored_name in stored_names:
            try:
                self.storage.delete_file_from_storage(stored_name)
            except Exception:
                pass

        self.repo.delete_note(note_id)
        return True


    def like_note(self, note_id: str, user_id: int) -> dict:
        """Regista o gosto do utilizador e devolve a contagem atualizada."""
        note = self.repo.get_by_id(note_id)

        if note is None:
            raise HTTPException(
                status_code=404,
                detail="Apontamento não encontrado"
            )

        self.repo.add_like(note_id, user_id)
        return {"liked": True, "likes_count": self.repo.count_likes(note_id)}

    def delete_like(self, note_id: str, user_id: int) -> dict:
        """Remove o gosto do utilizador e devolve a contagem atualizada."""
        note = self.repo.get_by_id(note_id)

        if note is None:
            raise HTTPException(
                status_code=404,
                detail="Apontamento não encontrado"
            )
        self.repo.remove_like(note_id, user_id)

        return {"liked": False, "likes_count": self.repo.count_likes(note_id)}