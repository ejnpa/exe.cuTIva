from pydantic import BaseModel, ConfigDict, EmailStr

class UserCreate(BaseModel):
    """Dados necessários para criar uma conta."""

    username: str
    email: EmailStr
    password: str

class UserPublic(BaseModel):
    """Campos de utilizador que podem ser enviados ao cliente."""

    id: int
    username: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)