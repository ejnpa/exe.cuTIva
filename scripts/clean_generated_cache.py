


def main() -> None:
    """Abre uma sessão da base de dados, seleciona o fornecedor de armazenamento e remove os artefactos expirados não guardados. Fecha sempre a sessão no bloco finally.
    """
    db = sessionLocal()
    
    try:
        storage = get_storage_provider()
        repo = GeneratedCacheRepository(
            db=db,
            ttl_days= settings.generated_cache_ttl_days
        )

        deleted_count = repo.delete_expired(storage)
        print(f"Artefactos expirados eliminados: {deleted_count}")
    finally:
        db.close()
        
if __name__ == "__main__": 
    main()
