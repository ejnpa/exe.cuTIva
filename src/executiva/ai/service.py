import requests

from executiva.core.config import settings
from executiva.ai.messages import AImessages

"""Comunica com o Ollama para adaptar texto inclusivo."""
class AIAccessibilityService:
    def __init__(self):
        """Prepara o endereço da API e escolhe o modelo de linguagem."""
        base_url = settings.ollama_url.rstrip("/")

        # Aceita tanto o endereço base como um endereço terminado em /api/generate.
        if base_url.endswith("/api/generate"):
            base_url = base_url.removesuffix("/api/generate")

        self.ollama_url = f"{base_url}/api/chat"
        self.model = "llama3"  # modelo a usar

    def adapt_text(self, text: str) -> str:

        """Limita o texto enviado, constrói as instruções de adaptação acessível
         e chama o Ollama. Devolve o texto gerado ou uma mensagem de erro controlada
          quando a ligação ou resposta falham.
        """
        if not text or len(text.strip()) < 10:
            return AImessages.ERROR_EXTRACTION

        # Limita o texto a 4000 caracteres para evitar sobrecarga
        short_text = text[:4000] if len(
            text) > 4000 else text

        messages = [
            {
                "role": "system",
                "content": AImessages.SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": f"Texto original para resumires e adaptares:\n\"\"\"\n{short_text}\n\"\"\"\n\nProduz apenas o resumo adaptado, sem preâmbulos."
            }
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.3}
        }

        try:

            response = requests.post(self.ollama_url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()


        except requests.exceptions.RequestException:
            return AImessages.ERROR_OLLAMA_DOWN
        except ValueError:
            # A resposta não era JSON válido.
            return AImessages.ERROR_BAD_FORMAT

        message =  data.get("message")
        content = message.get("content") if isinstance(message, dict) else None

        if not isinstance(content, str):
            return AImessages.ERROR_BAD_FORMAT

        return content.strip()




