from fastapi import APIRouter

from executiva.artifacts.router import router as artifact_router
from executiva.notes.router import router as notes_router
from executiva.users.router import router as users_router

api_router = APIRouter()

api_router.include_router(users_router)
api_router.include_router(artifact_router)
api_router.include_router(notes_router)