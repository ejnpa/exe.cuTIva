
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from executiva.api.router import api_router


app = FastAPI(
    title= "Notes API",
    description="API Restful para formatação de textos com foco em PHDA",
    version = "1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://100.89.13.43"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/")
def root():
    """Responde ao pedido da página inicial da API com uma mensagem de boas-vindas e o endereço da documentação interativa.
    """
    return {
        "message": "Bem-vindo à API!",
        "docs": "/docs"
    }
