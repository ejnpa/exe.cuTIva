from typing import Literal
from pydantic import BaseModel

class SavedArtifactRequest(BaseModel):
    """Dados enviados para gerar e guardar um artefacto na biblioteca."""
    note_id: str
    kind: Literal["summary", "audio"]
    variant: Literal["original", "adapted"] = "adapted"


class SavedArtifactResponse(BaseModel):
    """Confirmação devolvida depois de guardar o artefacto."""
    message: str

