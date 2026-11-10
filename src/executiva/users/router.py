from fastapi import APIRouter, Depends, HTTPException, Response, status, Form
from sqlalchemy.orm import Session

from executiva.core.config import settings
from executiva.db.session import get_db
from executiva.users.repository import UserRepository
from executiva.users.schemas import UserCreate, UserPublic
from executiva.users.service import UserService

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"]
)

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Cria o serviço de utilizadores para o pedido atual."""
    return UserService(repo=UserRepository(db))

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserPublic
)
def register_user(
    user: UserCreate,
    user_service: UserService = Depends(get_user_service)
) -> UserPublic:
    """Regista uma conta e devolve apenas os campos públicos."""
    new_user = user_service.register_new_user(
        user.username,
        user.email,
        user.password
    )
    if new_user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Existe uma conta com este email."
        )
    return UserPublic.model_validate(new_user)

@router.post("/login")
def login(
        response: Response,
        username: str = Form(...),
        password: str = Form(...),
        user_service: UserService = Depends(get_user_service)
):
    """Valida as credenciais e coloca o token num cookie HTTP-only."""

    token = user_service.authenticate_user(username, password)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas."
        )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure = settings.cookie_secure,
        path= "/",
        max_age= 60 * 60 * 24
    )

    return{"message": "Login efetuado com sucesso.", "username": username}

@router.post("/logout")
def logout(response: Response):
    """Remove do navegador o cookie que contém o token de sessão."""
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax",
        secure = settings.cookie_secure
    )
    return {"message": "Sessão terminada."}