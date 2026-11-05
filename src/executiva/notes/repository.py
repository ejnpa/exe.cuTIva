from sqlalchemy import func
from sqlalchemy.orm import Session

from executiva.notes.models import Notes, NoteLike


class NotesRepository:
    def __init__(self, db: Session):
        """Guarda a sessão SQLAlchemy usada por este repositório para consultar, criar e apagar apontamentos.
        """
        self.db = db

    def _format_notes(
            self,
            notes: list[Notes],
            current_user_id: int | None
    ) -> list[dict]:

        """Converte registos de apontamentos em dicionários para a API, substitui URLs internas de armazenamento por rotas da aplicação e acrescenta contagem de gostos e indicação de gosto do utilizador.
        """
        res = []
        for note in notes:
            item = {
                col.name: getattr(note, col.name)
                for col in note.__table__.columns
            }


            item["file_url"] = f"/api/notes/{note.id}/view"
            item["thumbnail_url"] = (
                f"/api/notes/{note.id}/thumbnail"
                    if note.thumbnail_url
                    else None
            )
            item ["likes"] = len(note.like_list)
            item["liked_by_user"] = any(
                like.user_id == current_user_id
                for like in note.like_list
            )
            res.append(item)
        return res

    def create(self, note_data: dict) -> Notes | None:
        """Cria um apontamento com os metadados fornecidos, confirma a transação e devolve o registo atualizado.
        """
        new_note = Notes(**note_data)
        self.db.add(new_note)
        self.db.commit()
        self.db.refresh(new_note)
        return new_note

    def delete_note(self, note_id: str):
        """Procura o apontamento pelo identificador e, se existir, remove-o da base de dados e confirma a transação.
        """
        note = self.get_by_id(note_id)
        if note is not None:
            self.db.delete(note)
            self.db.commit()


    def get_by_id(self, note_id: str) -> Notes | None:
        """Procura um apontamento pelo identificador e devolve o registo ou None se não existir.
        """
        return self.db.query(Notes).filter(Notes.id == note_id).first()

    def get_by_author(self, author_email: str, current_user_id: int | None = None):
        """Obtém os apontamentos de um autor e formata-os.
        """
        notes= self.db.query(Notes).filter(Notes.author == author_email).all()
        return self._format_notes(notes, current_user_id)

    def get_all_with_filters(
            self,
            school: str |None = None,
            course: str | None = None,
            year: str | None= None,
            subject: str | None = None,
            current_user_id: int | None= None
    ) -> list[dict]:

        """Constrói uma consulta de apontamentos aplicando apenas os filtros preenchidos. Os valores especiais Todos e Todas são tratados como ausência de filtro; o resultado é formatado para a API.
        """
        query = self.db.query(Notes)

        if school and school != "Todas":
            query = query.filter(Notes.school == school)
        if course and course != "Todos":
            query = query.filter(Notes.course == course)
        if year and year != "Todos":
            query = query.filter(Notes.year == year)
        if subject and subject != "Todas":
            query = query.filter(Notes.subject == subject)
        return self._format_notes(query.all(), current_user_id)

    def add_like(self, note_id: str, user_id: int) -> None:
        """Regista o gosto do utilizador, se ainda não existir."""
        existing_like = (
            self.db.query(NoteLike)
                         .filter(
                    NoteLike.note_id == note_id,
                            NoteLike.user_id == user_id )
            .first()
        )
        if existing_like is None:
            new_like = NoteLike(note_id=note_id, user_id=user_id)
            self.db.add(new_like)
            self.db.commit()

    def remove_like(self, note_id: str, user_id: int) -> None:
        """Remove o gosto do utilizador, se existir."""
        existing_like = (
            self.db.query(NoteLike)
            .filter(
                NoteLike.note_id== note_id,
                NoteLike.user_id == user_id
            )
            .first()
        )

        if existing_like is not None:
            self.db.delete(existing_like)
            self.db.commit()

    def count_likes(self, note_id: str) -> int:
        """Conta o número de gostos de um apontamento.
        """
        count = (
            self.db.query(func.count(NoteLike.user_id))
            .filter(NoteLike.note_id == note_id)
            .scalar()
        )
        return count if count is not None else 0




