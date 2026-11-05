import edge_tts

from collections.abc import AsyncIterator


class AudioService:
    """Gera áudio MP3 a partir de texto usando o Edge TTS."""
    voice = "pt-PT-RaquelNeural"

    async def stream_audio(self, text: str) -> AsyncIterator[bytes]:
        """Pede ao Edge TTS a síntese do texto e produz, à medida que chegam,
         apenas os blocos de áudio do fluxo.
        """
        if not text or not text.strip():
            return


        comm = edge_tts.Communicate(text.strip(), self.voice)
        async for chunk in comm.stream():
            if chunk.get("type") == "audio":
                audio_bytes = chunk.get("data")
                if audio_bytes:
                    yield audio_bytes

    async def synthesize(self, text: str) -> bytes:
        """Consome todos os blocos produzidos por stream_audio e junta-os num único conjunto de bytes MP3.
        """
        chunks = [
            chunk
            async for chunk in self.stream_audio(text)
        ]
        if not chunks:
            raise RuntimeError("O serviço de áudio não devolveu conteúdo.")
        return b"".join(chunks)


