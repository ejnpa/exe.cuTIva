import io
import sys
from types import SimpleNamespace

import pytest
import requests

from executiva.ai.messages import AImessages
from executiva.ai.service import AIAccessibilityService
from executiva.audio.service import AudioService
from executiva.notes.processors import image_extractor, pdf_generator, text_extractor


def test_ai_service_normalizes_ollama_url(monkeypatch):
    monkeypatch.setattr(
        "executiva.ai.service.settings.ollama_url",
        "http://ollama:11434/api/generate/",
    )

    service = AIAccessibilityService()

    assert service.ollama_url == "http://ollama:11434/api/chat"
    assert service.model == "llama3"


@pytest.mark.parametrize("text", [None, "", "   ", "curto"])
def test_ai_service_rejeita_texto_vazio_ou_curto(text):
    service = AIAccessibilityService()

    assert service.adapt_text(text) == AImessages.ERROR_EXTRACTION


def test_ai_service_envia_prompt_e_devolve_conteudo(monkeypatch):
    service = AIAccessibilityService()
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "  resumo adaptado  "}}

    def fake_post(url, json, timeout):
        captured.update(url=url, payload=json, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr("executiva.ai.service.requests.post", fake_post)

    result = service.adapt_text("Texto de teste suficientemente longo.")

    assert result == "resumo adaptado"
    assert captured["url"] == service.ollama_url
    assert captured["payload"]["model"] == service.model
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["messages"][1]["content"].endswith(
        "Texto de teste suficientemente longo.\n\"\"\"\n\nProduz apenas o resumo adaptado, sem preâmbulos."
    )
    assert captured["timeout"] == 60


def test_ai_service_limita_texto_a_4000_caracteres(monkeypatch):
    service = AIAccessibilityService()
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "resumo"}}

    def fake_post(url, json, timeout):
        captured["user_message"] = json["messages"][1]["content"]
        return FakeResponse()

    monkeypatch.setattr("executiva.ai.service.requests.post", fake_post)
    text = "x" * 5000

    service.adapt_text(text)

    # Isola o texto entre os delimitadores para não contar o "x" de "Texto".
    assert f'\n{"x" * 4000}\n"""' in captured["user_message"]


@pytest.mark.parametrize(
    "failure",
    [requests.exceptions.Timeout, requests.exceptions.ConnectionError],
)
def test_ai_service_devolve_erro_se_ollama_indisponivel(monkeypatch, failure):
    def fail(*args, **kwargs):
        raise failure("falha de ligação")

    monkeypatch.setattr("executiva.ai.service.requests.post", fail)

    result = AIAccessibilityService().adapt_text("Texto longo o suficiente.")

    assert result == AImessages.ERROR_OLLAMA_DOWN


def test_ai_service_devolve_erro_se_resposta_nao_for_json(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            raise ValueError("JSON inválido")

    monkeypatch.setattr(
        "executiva.ai.service.requests.post",
        lambda *args, **kwargs: FakeResponse(),
    )

    assert AIAccessibilityService().adapt_text(
        "Texto longo o suficiente."
    ) == AImessages.ERROR_BAD_FORMAT


@pytest.mark.parametrize("payload", [{}, {"message": None}, {"message": {}}])
def test_ai_service_devolve_erro_se_resposta_nao_tiver_conteudo(
    monkeypatch,
    payload,
):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return payload

    monkeypatch.setattr(
        "executiva.ai.service.requests.post",
        lambda *args, **kwargs: FakeResponse(),
    )

    assert AIAccessibilityService().adapt_text(
        "Texto longo o suficiente."
    ) == AImessages.ERROR_BAD_FORMAT


def test_ai_service_propaga_erro_nao_de_rede_da_resposta(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            raise RuntimeError("erro inesperado")

    monkeypatch.setattr(
        "executiva.ai.service.requests.post",
        lambda *args, **kwargs: FakeResponse(),
    )

    with pytest.raises(RuntimeError, match="erro inesperado"):
        AIAccessibilityService().adapt_text("Texto longo o suficiente.")


@pytest.mark.anyio
async def test_audio_service_stream_so_devolve_blocos_de_audio(monkeypatch):
    class FakeCommunicate:
        def __init__(self, text, voice):
            assert text == "Olá"
            assert voice == "pt-PT-RaquelNeural"

        async def stream(self):
            yield {"type": "metadata", "data": b"ignorar"}
            yield {"type": "audio", "data": b"parte-1"}
            yield {"type": "audio", "data": b"parte-2"}
            yield {"type": "audio", "data": b""}

    monkeypatch.setattr("executiva.audio.service.edge_tts.Communicate", FakeCommunicate)
    chunks = [
        chunk
        async for chunk in AudioService().stream_audio("  Olá  ")
    ]

    assert chunks == [b"parte-1", b"parte-2"]


@pytest.mark.anyio
async def test_audio_service_synthesize_junta_blocos_do_fluxo(monkeypatch):
    async def fake_audio_stream(self, text):
        assert text == "  Olá  "
        yield b"parte-1"
        yield b"parte-2"

    monkeypatch.setattr(AudioService, "stream_audio", fake_audio_stream)

    result = await AudioService().synthesize("  Olá  ")

    assert result == b"parte-1parte-2"


@pytest.mark.parametrize("text", ["", "  ", "\n\t"])
@pytest.mark.anyio
async def test_audio_service_rejeita_fluxo_vazio(text, monkeypatch):
    async def empty_audio_stream(self, value):
        if False:  # Define explicitamente um gerador assíncrono sem blocos.
            yield b""

    monkeypatch.setattr(AudioService, "stream_audio", empty_audio_stream)

    with pytest.raises(RuntimeError, match="não devolveu conteúdo"):
        await AudioService().synthesize(text)


def test_text_extractor_rejeita_extensao_nao_suportada():
    assert text_extractor.extract_text_from_file(b"dados", "ficheiro.txt") == ""


def test_text_extractor_extrai_pdf_com_todas_as_paginas(monkeypatch):
    class FakePage:
        def __init__(self, content):
            self.content = content

        def get_textpage(self):
            return self

        def get_text_range(self):
            return self.content

    class FakePDF:
        def __init__(self, data):
            assert data == b"pdf"
            self.pages = [FakePage("página 1"), FakePage("página 2")]
            self.closed = False

        def __iter__(self):
            return iter(self.pages)

        def close(self):
            self.closed = True

    monkeypatch.setattr(
        text_extractor,
        "pdfium",
        SimpleNamespace(PdfDocument=FakePDF),
    )

    result = text_extractor.extract_text_from_file(b"pdf", "a.PDF")

    assert result == "página 1\n\npágina 2"


def test_text_extractor_devolve_vazio_se_motor_pdf_ausente(monkeypatch):
    monkeypatch.setattr(text_extractor, "pdfium", None)

    assert text_extractor.extract_text_from_file(b"pdf", "a.pdf") == ""


def test_text_extractor_extrai_docx(monkeypatch):
    class FakeParagraph:
        def __init__(self, text):
            self.text = text

    class FakeDocument:
        def __init__(self, stream):
            assert isinstance(stream, io.BytesIO)
            self.paragraphs = [FakeParagraph("linha 1"), FakeParagraph("linha 2")]

    monkeypatch.setattr(
        text_extractor,
        "docx",
        SimpleNamespace(Document=FakeDocument),
    )

    assert text_extractor.extract_text_from_file(b"docx", "a.docx") == (
        "linha 1\nlinha 2"
    )


def test_text_extractor_captura_erro_do_extrator(monkeypatch):
    monkeypatch.setitem(
        text_extractor.SUPPORTED_EXTRACTORS,
        ".pdf",
        lambda data: (_ for _ in ()).throw(RuntimeError("PDF inválido")),
    )

    assert text_extractor.extract_text_from_file(b"x", "a.pdf") == ""


def test_thumbnail_devolve_none_para_extensao_nao_pdf(monkeypatch):
    monkeypatch.setattr(image_extractor, "pdfium", object())

    assert image_extractor.generate_pdf_thumbnail_bytes(b"dados", "a.png") is None


def test_thumbnail_devolve_png_da_primeira_pagina(monkeypatch):
    class FakeImage:
        def save(self, destination, format):
            assert format == "PNG"
            destination.write(b"png-falso")

    class FakePage:
        def render(self, scale):
            assert scale == 1
            return SimpleNamespace(to_pil=lambda: FakeImage())

    class FakePDF:
        def __init__(self, data):
            self.page = FakePage()

        def __getitem__(self, index):
            assert index == 0
            return self.page

    monkeypatch.setattr(
        image_extractor,
        "pdfium",
        SimpleNamespace(PdfDocument=FakePDF),
    )

    assert image_extractor.generate_pdf_thumbnail_bytes(
        b"pdf", "a.pdf"
    ) == b"png-falso"


def test_thumbnail_retorna_none_se_renderizacao_falhar(monkeypatch):
    class FakePDF:
        def __init__(self, data):
            raise RuntimeError("PDF danificado")

    monkeypatch.setattr(
        image_extractor,
        "pdfium",
        SimpleNamespace(PdfDocument=FakePDF),
    )

    assert image_extractor.generate_pdf_thumbnail_bytes(b"pdf", "a.pdf") is None


def test_bionic_reader_formata_palavras_curta_e_longas():
    result = pdf_generator._bionic_reader("Olá estudo acessível")

    assert result == "<b>Olá</b> <b>est</b>udo <b>acess</b>ível"


def test_pdf_generator_escapa_titulo_e_sanitiza_html(monkeypatch):
    captured = {}

    class FakeHTML:
        def __init__(self, string):
            captured["html"] = string

        def write_pdf(self):
            return b"pdf-falso"

    # O import real pode falhar em Windows se as bibliotecas nativas do
    # WeasyPrint não estiverem instaladas; o teste só precisa substituir HTML.
    monkeypatch.setitem(sys.modules, "weasyprint", SimpleNamespace(HTML=FakeHTML))

    result = pdf_generator.create_acessability_pdf(
        "<script>alert('x')</script>",
        "# Título\n\nTexto <script>malicioso</script>",
    )

    assert result == b"pdf-falso"
    assert "&lt;script&gt;" in captured["html"]
    assert "<script>malicioso</script>" not in captured["html"]
