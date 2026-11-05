from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status, Request
from jose import jwt,JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from executiva.core.config import settings
from executiva.db.session import get_db
from executiva.users.models import User
from executiva.users.repository import UserRepository



ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60*24  # 1 day

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compara uma palavra-passe em texto simples com o hash guardado. O contexto passlib trata do algoritmo e dos parâmetros usados no hash.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Gera um hash bcrypt da palavra-passe para guardar na base de dados sem persistir o texto original.
    """
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    """Cria um JWT assinado com os dados recebidos e uma data de expiração. O identificador do utilizador é colocado no campo sub pelo serviço de autenticação.
    """
    payload= data.copy()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload["exp"] = expires_at

    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

def _get_token_from_cookie(request: Request) -> str:
    """Lê o cookie HTTP-only access_token do pedido. Se o cookie não existir, interrompe o pedido com HTTP 401.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="É necessário iniciar sessão.")
    return token

def get_current_user(
        request: Request,
        db: Session = Depends(get_db),
         ) -> User:
    """Valida a assinatura e a expiração do JWT, procura o utilizador identificado por sub e devolve o registo. Tokens inválidos ou utilizadores inexistentes produzem HTTP 401.
    """
    token = _get_token_from_cookie(request)

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possivel validar credenciais"
    )

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM]
        )
        email = payload.get("sub")
        if not isinstance(email,str) or not email:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = UserRepository(db).get_by_email(email)
    if user is None:
        raise credentials_exception

    return user

