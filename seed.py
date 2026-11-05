import os
from dotenv import load_dotenv

load_dotenv()  # Carrega as variáveis de ambiente do ficheiro .env

from executiva.db.session import SessionLocal, engine
from executiva.db.base import Base
from executiva.users.models import User
from executiva.core.security import get_password_hash


def criar_utilizadores_teste():
    """Cria dez contas de teste com a mesma palavra-passe de demonstração. Remove primeiro os utilizadores existentes e reverte a transação se ocorrer um erro.
    """
    db_url=os.getenv("DATABASE_URL")
    print(f"A usar a base de dados: {db_url}")
    
    
    Base.metadata.create_all(bind=engine)
    
    db=SessionLocal()
     
    try:
        print("A limpar utilizadores antigos e a criar 10 novos...")
        db.query(User).delete()
        
        for i in range(1, 11):
            novo_utilizador = User(
                username=f"Estudante{i}",
                email=f"aluno{i}@ipcb.pt",
                password=get_password_hash("senha123")
            )
            db.add(novo_utilizador)
        db.commit()    
        print("✅ 10 utilizadores criados com sucesso na Nuvem (PostgreSQL)!")   
            
    except Exception as e:
        print(f"❌ Erro ao popular base de dados: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    criar_utilizadores_teste()        