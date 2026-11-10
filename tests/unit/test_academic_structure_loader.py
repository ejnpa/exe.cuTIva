import json

from executiva.academic_structure import loader


def test_load_structure_le_ficheiro_de_dados_real():
    structure = loader.load_structure()

    assert isinstance(structure, (dict, list))
    assert structure


def test_load_structure_devolve_aviso_se_ficheiro_nao_existir(monkeypatch):
    monkeypatch.setattr(loader.Path, "exists", lambda self: False)

    assert loader.load_structure() == {
        "avisos": "Ficheiro de estrutura não encontrado."
    }


def test_load_structure_devolve_aviso_se_json_for_invalido(monkeypatch):
    class FakeFile:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, *args):
            return "{ json incompleto"

    monkeypatch.setattr(loader.Path, "exists", lambda self: True)
    monkeypatch.setattr(loader.Path, "open", lambda *args, **kwargs: FakeFile())

    result = loader.load_structure()

    assert result["avisos"].startswith("Erro ao carregar dados da escola:")
    assert "JSON" in result["avisos"] or "Expecting" in result["avisos"]
