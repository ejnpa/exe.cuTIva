from datetime import timezone, timedelta, datetime

from sqlalchemy.orm import Session

from executiva.artifacts.models import SavedArtifact, GeneratedCache
from executiva.notes.models import Notes

def _as_utc(value:datetime):
    """Normaliza uma data para UTC, incluindo datas sem fuso devolvidas pelo SQLite."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

class GeneratedCacheRepository:
    """Gere a cache de resumos e áudios e as referências guardadas na biblioteca."""
    def __init__(self, db: Session, ttl_days: int):
        """Guarda a sessão da base de dados e o prazo de validade usado para os registos de cache.
        """
        self.db = db
        self.ttl_days = ttl_days

    def get(self, cache_key: str) -> GeneratedCache | None:
        """Obtém uma entrada válida e atualiza a data da última utilização."""
        item = self.db.query(GeneratedCache).filter_by(cache_key=cache_key).first()
        if item is None:
            return None

        is_saved = (
                self.db.query(SavedArtifact.id)
                .filter_by(cache_key=cache_key)
                .first()
                is not None
        )

        now = datetime.now(timezone.utc)
        if item.expires_at and _as_utc(item.expires_at) <= now and not is_saved:
            return None

        item.last_used_at = now
        self.db.commit()
        return item

    def save(self, cache_key: str, **values) -> GeneratedCache:
        """Insere uma entrada de cache nova ou atualiza uma existente, renova o prazo de validade e confirma a transação.
        """
        item = self.db.query(GeneratedCache).filter_by(cache_key=cache_key).first()

        if item is None:
            item = GeneratedCache(cache_key=cache_key, **values)
            self.db.add(item)
        else:
            for name, value in values.items():
                setattr(item, name, value)
            item.last_used_at = datetime.now(timezone.utc)
            item.expires_at = datetime.now(timezone.utc) + timedelta(days=self.ttl_days)

        self.db.commit()
        self.db.refresh(item)
        return item

    def pin(self, user_id: int, cache_key: str) -> None:
        """Guarda uma referência ao artefacto na biblioteca do utilizador.
        Copia para o registo guardado os metadados disponíveis na cache,
        para a rotina de limpeza não o eliminar.
        """

        item = self.db.query(GeneratedCache).filter_by(cache_key=cache_key).first()

        if item is None:
            raise ValueError("O artefacto não existe na cache.")

        existing = (
            self.db.query(SavedArtifact)
            .filter_by(
                user_id=user_id,
                cache_key=cache_key)
            .first()
        )
        if existing is None:
            return

        note = self.db.query(Notes).filter_by(id=item.note_id).first()

        saved_item = SavedArtifact(
            user_id=user_id,
            cache_key=cache_key,
            note_id=item.note_id,
            note_title=note.title if note else "Apontamento",
            kind=item.kind,
            variant=item.variant,
            source_hash=item.source_hash,
            result_text=item.result_text,
            blob_name=item.blob_name
        )
        self.db.add(saved_item)
        self.db.commit()

    def unpin(self, user_id: int, cache_key: str):
        """Retira o artefacto da biblioteca e volta a aplicar o prazo de validade."""
        saved_item = (
            self.db.query(SavedArtifact)
            .filter_by(
                user_id=user_id,
                cache_key=cache_key)
            .first()
        )

        if saved_item is not None:
            self.db.delete(saved_item)
        self.db.flush()

        still_saved = (
            self.db.query(SavedArtifact.id)
            .filter_by(
                cache_key=cache_key)
            .first()
        )

        cache_item = (
            self.db.query(GeneratedCache)
            .filter_by(
                cache_key=cache_key)
            .first()
        )

        if cache_item is not None and not still_saved:
            cache_item.expires_at = (
                    datetime.now(timezone.utc)
                    + timedelta(days=self.ttl_days)
            )
        self.db.commit()

    def delete_expired(self, storage) -> int:
        """Apaga da base de dados e do storage os itens expirados não guardados."""
        now = datetime.now(timezone.utc)

        expired_items = (
            self.db.query(GeneratedCache)
            .filter(GeneratedCache.expires_at.is_not(None))
            .all()
        )

        deleted_count = 0

        for item in expired_items:
            if _as_utc(item.expires_at) > now:
                continue

            is_saved = (
                    self.db.query(SavedArtifact.id)
                    .filter_by(cache_key=item.cache_key)
                    .first()
                    is not None
            )
            if is_saved:
                continue

            if item.kind == "audio" and item.blob_name:
                storage.delete_cached_audio(item.blob_name)
            self.db.delete(item)
            deleted_count += 1

        self.db.commit()
        return deleted_count
