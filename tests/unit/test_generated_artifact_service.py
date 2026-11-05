from types import SimpleNamespace

import pytest

from executiva.artifacts.service import GeneratedArtifactService

class FakeCache:
    def __init__(self, cached_item):
        self.cached_item = cached_item

    def get(self, cache_key):
        return self.cached_item

class FakeAI:
    model = "modelo de teste"
    def adapt_text(self, text):
        raise AssertionError("A IA não devia ser chamada quando há cache.")


def test_reuses_cached_summary():
    cache = FakeCache(
        SimpleNamespace(result_text="Resumo guardado em cache", summary="summary")
    )
    service = GeneratedArtifactService(
            cache=cache,
            storage = None,
            ai_service=FakeAI(),
            audio_service=None,
            ttl_days=7
        )
    sumary, cache_key = service.get_or_create_summary(note_id="nota-123",text="Texto suficientemente longo para gerar um resumo.")

    assert sumary == "Resumo guardado em cache"
    assert len(cache_key) == 64

import asyncio


class RecordingCache:
    def __init__(self, cached_item=None):
        self.cached_item = cached_item
        self.saved = []

    def get(self, cache_key):
        return self.cached_item

    def save(self, cache_key, **values):
        self.saved.append((cache_key, values))


class FakeAIThatGenerates:
    model = "modelo-de-teste"

    def adapt_text(self, text):
        return "Resumo criado para o teste"


class FakeAudio:
    voice = "voz-de-teste"

    async def synthesize(self, text):
        return b"audio-de-teste"


class FakeStorage:
    def __init__(self):
        self.saved_audio = None

    def get_cached_audio(self, blob_name):
        return None

    def save_cached_audio(self, blob_name, data):
        self.saved_audio = (blob_name, data)


def test_cache_miss_generates_and_saves_summary():
    cache = RecordingCache()
    service = GeneratedArtifactService(
        cache=cache,
        storage=None,
        ai_service=FakeAIThatGenerates(),
        audio_service=None,
        ttl_days=7,
    )

    summary, cache_key = service.get_or_create_summary(
        "nota-123",
        "Texto de origem suficientemente longo para criar um resumo.",
    )

    assert summary == "Resumo criado para o teste"
    assert len(cache_key) == 64
    assert len(cache.saved) == 1
    assert cache.saved[0][1]["kind"] == "summary"


def test_ai_error_is_not_saved_in_cache():
    class FakeAIWithError:
        model = "modelo-de-teste"

        def adapt_text(self, text):
            return "Erro: serviço de IA indisponível"

    cache = RecordingCache()
    service = GeneratedArtifactService(
        cache=cache,
        storage=None,
        ai_service=FakeAIWithError(),
        audio_service=None,
        ttl_days=7,
    )

    with pytest.raises(RuntimeError):
        service.get_or_create_summary(
            "nota-123",
            "Texto de origem suficientemente longo para criar um resumo.",
        )

    assert cache.saved == []


def test_cache_miss_synthesizes_and_saves_audio():
    cache = RecordingCache()
    storage = FakeStorage()
    service = GeneratedArtifactService(
        cache=cache,
        storage=storage,
        ai_service=None,
        audio_service=FakeAudio(),
        ttl_days=7,
    )

    audio_bytes, cache_key = asyncio.run(
        service.get_or_create_audio(
            note_id="nota-123",
            variant="original",
            text="Texto para sintetizar",
        )
    )

    assert audio_bytes == b"audio-de-teste"
    assert len(cache_key) == 64
    assert storage.saved_audio == (f"{cache_key}.mp3", b"audio-de-teste")
    assert len(cache.saved) == 1
    assert cache.saved[0][1]["kind"] == "audio"