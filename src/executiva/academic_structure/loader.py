import json
from pathlib import Path


def load_structure():
    """Lê o JSON com a estrutura de escolas, cursos, anos e disciplinas
    para popular os dropdowns."""

    filepath = Path(__file__).with_name("data.json")
    try:
        if filepath.exists():
            with filepath.open( "r", encoding="utf-8") as f:
                return json.load(f)
        return {"avisos": "Ficheiro de estrutura não encontrado."}
    except Exception as e:
        print(f"Erro ao carregar dados da escola: {e}")
        return {"avisos": f"Erro ao carregar dados da escola: {e}"}