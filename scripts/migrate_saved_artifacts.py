"""Copy saved cache references from the legacy table into the current schema.

Run once after deploying the application version that defines the current models:
    python -m scripts.migrate_saved_artifacts
"""
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker


def main() -> None:
    # Creates the current table if this is a fresh database. It does not alter
    # existing tables, which is why the legacy rows are copied explicitly.
    """Cria a tabela atual se necessário, acrescenta a coluna cache_key a esquemas intermédios e copia referências do nome de tabela legado. Os registos sem entrada correspondente na cache são preservados na tabela antiga.
    """
    from models import Base
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    current_table = "saved_atifacts"
    if current_table in inspector.get_table_names():
        current_columns = {column["name"] for column in inspector.get_columns(current_table)}
        if "cache_key" not in current_columns:
            with engine.begin() as connection:
                connection.execute(text(f'ALTER TABLE "{current_table}" ADD COLUMN cache_key VARCHAR(64)'))
            Session = sessionmaker(bind=engine)
            with Session() as db:
                rows = db.execute(text(
                    f'SELECT id, note_id, kind, variant, source_hash FROM "{current_table}" WHERE cache_key IS NULL'
                )).all()
                for row_id, note_id, kind, variant, source_hash in rows:
                    cached = db.query(GeneratedCache).filter_by(
                        note_id=note_id, kind=kind, variant=variant, source_hash=source_hash
                    ).first()
                    if cached:
                        db.execute(text(
                            f'UPDATE "{current_table}" SET cache_key=:cache_key WHERE id=:row_id'
                        ), {"cache_key": cached.cache_key, "row_id": row_id})
                db.commit()

        # PostgreSQL enforces VARCHAR lengths. The previous snapshot schema
        # used 16 characters for hashes and blob names, shorter than the cache keys.
        if engine.dialect.name == "postgresql":
            existing = {column["name"] for column in inspect(engine).get_columns(current_table)}
            with engine.begin() as connection:
                if "source_hash" in existing:
                    connection.execute(text(f'ALTER TABLE "{current_table}" ALTER COLUMN source_hash TYPE VARCHAR(64)'))
                if "blob_name" in existing:
                    connection.execute(text(f'ALTER TABLE "{current_table}" ALTER COLUMN blob_name TYPE VARCHAR(255)'))

    legacy_table = next(
        (name for name in ("saved_atifact", "saved_artifact") if name in inspector.get_table_names()),
        None,
    )
    if not legacy_table:
        print("Não foi encontrada uma tabela antiga de artefactos guardados.")
        return

    columns = {column["name"] for column in inspector.get_columns(legacy_table)}
    if not {"user_id", "cache_key"}.issubset(columns):
        print(f"A tabela {legacy_table} não tem as colunas esperadas; não foi alterada.")
        return

    Session = sessionmaker(bind=engine)
    copied = skipped = 0
    with Session() as db:
        rows = db.execute(text(f'SELECT user_id, cache_key FROM "{legacy_table}"')).all()
        for user_id, cache_key in rows:
            if db.query(SavedArtifact.id).filter_by(user_id=user_id, cache_key=cache_key).first():
                continue
            cached = db.query(GeneratedCache).filter_by(cache_key=cache_key).first()
            if cached is None:
                skipped += 1
                continue
            note = db.query(Notes).filter_by(id=cached.note_id).first()
            db.add(SavedArtifact(
                user_id=user_id,
                cache_key=cache_key,
                note_id=cached.note_id,
                note_title=note.title if note else "Apontamento",
                kind=cached.kind,
                variant=cached.variant,
                source_hash=cached.source_hash,
                result_text=cached.result_text,
                blob_name=cached.blob_name,
            ))
            copied += 1
        db.commit()

    print(f"Artefactos migrados: {copied}; referências sem cache preservadas na tabela antiga: {skipped}.")


if __name__ == "__main__":
    main()
