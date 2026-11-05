from sqlalchemy.orm import Session

from  executiva.users.models import User


class UserRepository:
    def __init__(self, db: Session):
        """Guarda a sessão SQLAlchemy que este repositório utilizará nas consultas e operações sobre utilizadores.
        """
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        """Procura um utilizador pelo endereço de email e devolve o primeiro resultado, ou None se não existir.
        """
        return self.db.query(User).filter(User.email == email).first()

    def create(self, user_data: dict) -> User:
        """Cria um registo de utilizador, confirma a transação e atualiza a instância para incluir os valores atribuídos pela base de dados.
        """
        new_user = User(**user_data)
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        return new_user