from pydantic import BaseModel, ConfigDict


class NotePublic(BaseModel):
    """Metadados de um apontamento visíveis na API."""

    id: str
    title: str
    school: str
    course: str
    year: str
    subject: str
    author: str
    file_url: str
    thumbnail_url: str | None = None
    likes: int = 0
    liked_by_user: bool = False

    model_config = ConfigDict(from_attributes=True)

class NoteContent(NotePublic):
    content: str

