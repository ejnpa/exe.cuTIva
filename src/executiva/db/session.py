from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from executiva.core.config import settings

DATABASE_URL = settings.database_url

engine_options = {}

if DATABASE_URL.startswith("sqlite"):
    engine_options ["connect_args"]={"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_options)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db():
    """Disponibiliza uma sessão SQLAlchemy a cada pedido HTTP. A sessão é criada antes de o endpoint executar e fechada no bloco finally, mesmo que ocorra uma exceção, para libertar a ligação à base de dados.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()