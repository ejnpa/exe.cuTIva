from executiva.core.security import (
    create_access_token,
    get_password_hash,
    verify_password
)
from executiva.users.repository import UserRepository

class UserService:
    def __init__(self, repo: UserRepository):
        """Recebe e conserva o repositório que executa as operações de persistência de utilizadores.
        """
        self.repo = repo

    def register_new_user(self, username: str, email: str, password: str):
        """Verifica se o email já está registado, cria o hash da palavra-passe e pede ao repositório para guardar o novo utilizador. Devolve None quando o email já existe.
        """
        existing_user = self.repo.get_by_email(email)
        if existing_user:
            return None

        hashed_password = get_password_hash(password)

        user_data = {
            "username": username,
            "email": email,
            "password": hashed_password
        }
        return self.repo.create(user_data)

    def authenticate_user(self, email: str, password: str) -> str | None:
        """Procura a conta pelo email e verifica a palavra-passe. Se as credenciais forem válidas, devolve um JWT; caso contrário, devolve None.
        """
        user = self.repo.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.password):
            return None

        return create_access_token(data={"sub": user.email})