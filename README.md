# App de Cardapio Escolar

Aplicativo integrador focado em divulgar o cardapio escolar, registrar avisos e reunir dados para gerar insights para a escola. Este repositório contem o prototipo de banco de dados local (SQLite) e uma API FastAPI para integracao com o front-end.

## Requisitos
- Python 3.10+ instalado
- Pip atualizado (`py -m pip install --upgrade pip`)
- Dependencias do projeto:
	```powershell
	py -m pip install fastapi uvicorn sqlalchemy pydantic
	```

## Estrutura Principal
- `db_setup.py`: define o modelo relacional via SQLAlchemy, cria o arquivo `bd_teste.sqlite` e popula dados de exemplo quando vazio.
- `api.py`: API REST que expõe as operacoes de ingredientes, refeicoes e cardapio semanal.
- `bd_teste.sqlite`: banco SQLite gerado automaticamente (pode ser removido para recriar do zero).

## Banco de Dados
A estrutura de dados e composta por quatro tabelas relacionadas:
1. `bd_ingredientes`: armazena os ingredientes com informacoes nutricionais, alergeno e preco medio.
2. `bd_refeicoes`: registra pratos/ refeicoes disponiveis.
3. `bd_pratos_ingredientes`: tabela ponte entre refeicoes e ingredientes, com quantidade e unidade.
4. `bd_cardapio_semanal`: agenda as refeicoes por dia da semana e tipo (ex.: Almoco).

As relacoes possuem chaves estrangeiras com delecao em cascata e restricoes de valores nao negativos.

## Como Executar
1. Gere o banco (caso ainda nao exista) executando:
	 ```powershell
	 py db_setup.py
	 ```
2. Suba a API em modo desenvolvimento:
	 ```powershell
	 uvicorn api:app --reload
	 ```
3. Acesse `http://127.0.0.1:8000/` para ver o guia rapido de integracao. Documentacao interativa disponivel em `/docs` e `/redoc`.

## Endpoints Principais
- `GET /ingredientes`: lista ingredientes cadastrados.
- `POST /ingredientes`: cria ingrediente. Payload segue o esquema `IngredienteCreate`.
- `GET /refeicoes`: detalha refeicoes com ingredientes e agenda.
- `POST /refeicoes`: cria refeicao usando ids de ingredientes existentes e opcionalmente agenda semanal.
- `GET /cardapio`: consulta o cardapio com filtros opcionais `dia` e `tipo`.

Consulte a raiz da API ou o Swagger para ver exemplos completos de JSON.

## Inserindo Dados via Script
Importe as estruturas utilitarias para popular o cardapio em qualquer terminal Python:
```python
from db_setup import criar_engine, criar_cardapio, NovoIngrediente, NovaRefeicao, Alergeno, Macronutriente

engine = criar_engine()

frango = NovoIngrediente(
		nome="Frango grelhado",
		valor_energetico=165,
		alergenico=Alergeno.SOJA,
		macronutriente=Macronutriente.PROTEINAS,
		quantidade=200,
		unidade_medida="g",
		preco_medio=12.90,
)

refeicao = NovaRefeicao(
		nome_prato="Frango com arroz integral",
		descricao="Prato completo para o almoco",
		ingredientes=[(frango, 150, "g")],
)

criar_cardapio(engine, refeicao, [("Segunda", "Almoco")])
```

## Dicas
- Remova `bd_teste.sqlite` para reiniciar o banco; o script recria e repopula com exemplos.
- Use ferramentas como DB Browser for SQLite para inspecionar as tabelas.
- Sempre mantenha a sessao `uvicorn` em execucao enquanto o front-end consumir a API.
