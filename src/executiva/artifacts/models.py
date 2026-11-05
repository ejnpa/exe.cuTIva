from datetime import datetime, timezone
from sqlalchemy import(
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint
)

from executiva.db.base import Base

def utc_now():
    """Devolve a data e hora atuais em UTC para preencher as datas de criação e
    utilização da cache.
    """
    return datetime.now(timezone.utc)


class GeneratedCache(Base):
    """Representa um resumo ou áudio gerado e temporariamente guardado em cache."""
    __tablename__ = "generated_cache"

    cache_key = Column(String(64), primary_key=True)
    note_id = Column(
        String,
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    kind = Column(String(16), nullable=False)
    variant = Column(String(16), nullable=False)
    source_hash = Column(String(64), nullable=False)

    result_text = Column(Text, nullable=True)
    blob_name = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_used_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class SavedArtifact(Base):
    """Representa um artefacto de cache guardado na biblioteca de um utilizador."""
    __tablename__ = "saved_atifacts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    cache_key = Column(
        String(64),
        ForeignKey("generated_cache.cache_key", ondelete="CASCADE"),
        nullable=False
    )

    note_id = Column(String, nullable=False)
    note_title = Column(String, nullable=False)
    kind = Column(String(16), nullable=False)
    variant = Column(String(16), nullable=False)
    source_hash = Column(String(64), nullable=False)
    result_text = Column(Text, nullable=True)
    blob_name = Column(String(255), nullable=True)
    saved_at = Column(DateTime(timezone=True), default= utc_now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "cache_key",
            name="uq_saved_artifact_version"
        ),
    )