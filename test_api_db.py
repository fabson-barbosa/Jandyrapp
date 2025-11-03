from __future__ import annotations

import os
import sys
from pprint import pprint
from uuid import uuid4

import requests
from sqlalchemy.orm import Session

from db_setup import BdAluno, BdCardapioSemanal, BdRefeicao, NovoAluno, cadastrar_aluno, criar_engine, criar_tabelas

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def _check_response(response: requests.Response, context: str) -> dict | list:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:  # pragma: no cover - manual test helper
        print(f"Falha em {context}: {exc}")
        try:
            pprint(response.json())
        except Exception:  # pylint: disable=broad-except
            print(response.text)
        sys.exit(1)
    try:
        return response.json() if response.content else {}
    except ValueError:
        return {}


def testar_api() -> None:
    print("== Testando API ==")
    raiz = _check_response(requests.get(BASE_URL, timeout=5), "GET /")
    print("Guia da raiz:")
    pprint(raiz)

    sufixo = uuid4().hex[:6]
    ingredientes_payload = [
        {
            "nome": f"Quinoa Teste {sufixo}",
            "valor_energetico": 368,
            "alergenico": "Glúten",
            "macronutriente": "Carboidratos",
            "quantidade": 100,
            "unidade_medida": "g",
            "preco_medio": 16.5,
        },
        {
            "nome": f"Grão-de-bico Teste {sufixo}",
            "valor_energetico": 164,
            "alergenico": "Soja",
            "macronutriente": "Proteínas",
            "quantidade": 80,
            "unidade_medida": "g",
            "preco_medio": 12.3,
        },
    ]

    ingredientes_criados = []
    for payload in ingredientes_payload:
        resp = _check_response(requests.post(f"{BASE_URL}/ingredientes", json=payload, timeout=5), "POST /ingredientes")
        ingredientes_criados.append(resp)
    print("Ingredientes criados:")
    pprint(ingredientes_criados)

    lista_ingredientes = _check_response(requests.get(f"{BASE_URL}/ingredientes", timeout=5), "GET /ingredientes")
    print("Total de ingredientes cadastrados:", len(lista_ingredientes))

    refeicao_payload = {
        "nome_prato": f"Bowl Energético {sufixo}",
        "descricao": "Quinoa e grão-de-bico com temperos leves.",
        "ingredientes": [
            {"id_ingrediente": ingredientes_criados[0]["id_ingrediente"], "quantidade": 60, "unidade_medida": "g"},
            {"id_ingrediente": ingredientes_criados[1]["id_ingrediente"], "quantidade": 80, "unidade_medida": "g"},
        ],
        "cardapio": [
            {"dia_da_semana": "Terça", "tipo_refeicao": "Almoço"},
            {"dia_da_semana": "Quinta", "tipo_refeicao": "Jantar"},
        ],
    }

    refeicao_criada = _check_response(requests.post(f"{BASE_URL}/refeicoes", json=refeicao_payload, timeout=5), "POST /refeicoes")
    print("Refeição criada:")
    pprint(refeicao_criada)

    refeicoes = _check_response(requests.get(f"{BASE_URL}/refeicoes", timeout=5), "GET /refeicoes")
    print("Total de refeições cadastradas:", len(refeicoes))

    cardapio = _check_response(requests.get(f"{BASE_URL}/cardapio", timeout=5), "GET /cardapio")
    print("Registros do cardápio semanal:", len(cardapio))
    cardapio_filtro = _check_response(
        requests.get(f"{BASE_URL}/cardapio", params={"dia": "Terça"}, timeout=5),
        "GET /cardapio?dia=Terça",
    )
    print("Registros no cardápio para Terça:", len(cardapio_filtro))


def testar_banco() -> None:
    print("\n== Testando acesso direto ao banco ==")
    engine = criar_engine()
    criar_tabelas(engine)

    sufixo = uuid4().hex[:6]
    novo_aluno = NovoAluno(
        nome=f"Aluno Teste {sufixo}",
        ra=f"RA-{sufixo}",
        serie="5º ano",
        periodo="Matutino",
        alergias=["Glúten", "Leite"],
        hobbies=["Futebol", "Desenho"],
        dificuldades=["Foco e concentração", "Matemática"],
        observacoes="Gerado automaticamente para testes.",
        nome_turma="Turma Teste",
    )

    cadastrar_aluno(engine, novo_aluno)
    print(f"Aluno {novo_aluno.nome} cadastrado com sucesso.")

    with Session(engine) as session:
        aluno_db = (
            session.query(BdAluno)
            .filter(BdAluno.serie == novo_aluno.serie, BdAluno.periodo == novo_aluno.periodo)
            .order_by(BdAluno.id_aluno.desc())
            .first()
        )
        if aluno_db is None:
            raise RuntimeError("Aluno recém-cadastrado não encontrado no banco.")

        print("Dados do aluno (nome/RA já descriptografados):")
        pprint(
            {
                "id_aluno": aluno_db.id_aluno,
                "nome": aluno_db.nome,
                "ra": aluno_db.ra,
                "serie": aluno_db.serie,
                "periodo": aluno_db.periodo,
                "observacoes": aluno_db.observacoes,
                "turma": aluno_db.turma.nome_turma if aluno_db.turma else None,
            }
        )

        alergias = [a.descricao for a in aluno_db.alergias]
        hobbies = [h.descricao for h in aluno_db.hobbies]
        dificuldades = [d.descricao for d in sorted(aluno_db.dificuldades, key=lambda item: item.ordem)]
        print("Listas associadas:")
        pprint({"alergias": alergias, "hobbies": hobbies, "dificuldades": dificuldades})

    total_cardapio = session.query(BdCardapioSemanal).count()
    total_refeicoes = session.query(BdRefeicao).count()
    print(f"Resumo: {total_cardapio} entradas de cardápio e {total_refeicoes} refeições registradas.")


def main() -> None:
    try:
        testar_api()
    except requests.ConnectionError as exc:  # pragma: no cover - manual execution helper
        print("Não foi possível conectar à API. Certifique-se de que o uvicorn está em execução.")
        print(exc)
        sys.exit(1)

    testar_banco()
    print("\nTodos os testes foram concluídos com sucesso.")


if __name__ == "__main__":
    main()
