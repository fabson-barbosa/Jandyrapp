# App de Cardapio Escolar

Aplicativo integrador focado em divulgar o cardapio escolar, registrar avisos e reunir dados para gerar insights para a escola. Este repositório contem o prototipo de banco de dados local (SQLite) e uma API FastAPI para integracao com o front-end.

## Requisitos
- Python 3.10+ instalado
- Pip atualizado (`py -m pip install --upgrade pip`)
- Dependencias do projeto:
  ```powershell
	py -m pip install fastapi uvicorn sqlalchemy pydantic cryptography requests
  ```

## Estrutura Principal
- `db_setup.py`: define o modelo relacional via SQLAlchemy, cria o arquivo `bd_teste.sqlite`, gera a chave de criptografia `aluno.key` e popula dados de exemplo quando vazio.
- `api.py`: API REST que expõe as operacoes de ingredientes, refeicoes e cardapio semanal.
- `bd_teste.sqlite`: banco SQLite gerado automaticamente (pode ser removido para recriar do zero).
- `aluno.key`: chave Fernet usada para criptografar/descriptografar nome e RA dos alunos (é criada quando o script roda pela primeira vez).
- `test_api_db.py`: script que executa chamadas completas na API e valida o cadastro de alunos diretamente no banco.

## Banco de Dados
A estrutura de dados e composta por tabelas relacionadas:
1. `bd_ingredientes`: armazena os ingredientes com informacoes nutricionais, alergeno e preco medio.
2. `bd_refeicoes`: registra pratos/ refeicoes disponiveis.
3. `bd_pratos_ingredientes`: tabela ponte entre refeicoes e ingredientes, com quantidade e unidade.
4. `bd_cardapio_semanal`: agenda as refeicoes por dia da semana e tipo (ex.: Almoco).
5. `bd_turmas`: agrupa alunos por serie e periodo; o campo `nome_turma` e opcional.
6. `bd_alunos`: registra dados do aluno, com campos `nome` e `ra` criptografados (Fernet). Mantem serie, periodo, observacoes e referencia a uma turma.
7. `bd_alunos_alergenicos`, `bd_alunos_hobbies`, `bd_alunos_dificuldades`: armazenam as listas dinamicas do formulario (dificuldades preservam a ordem).

As relacoes possuem chaves estrangeiras com delecao em cascata (ou `SET NULL`, no caso de turmas) e restricoes de valores nao negativos. Campos sensiveis de alunos sao criptografados automaticamente antes de persistir.

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

### Cadastrando alunos
```python
from db_setup import cadastrar_aluno, NovoAluno, criar_engine

engine = criar_engine()

aluno = NovoAluno(
	nome="Maria Oliveira",
	ra="2025-010",
	serie="5º ano",
	periodo="Matutino",
	alergias=["Gluten", "Leite"],
	hobbies=["Danca", "Desenho"],
	dificuldades=["Foco e concentracao", "Matematica"],
	observacoes="Prefere atividades em grupo",
	nome_turma="Turma A",
)

cadastrar_aluno(engine, aluno)
```

### Roteiro de teste completo
Com o servidor `uvicorn` em execução, rode:
```powershell
py test_api_db.py
```
O script cria ingredientes, refeições e agenda via API, consulta os dados para validar e, em seguida, cadastra um aluno diretamente no banco verificando se os relacionamentos foram persistidos.

## Dicas
- Remova `bd_teste.sqlite` para reiniciar o banco; o script recria e repopula com exemplos.
- Para gerar uma nova chave de criptografia, remova `aluno.key` (isso torna ilegíveis os dados de alunos gravados com a chave anterior).
- Use ferramentas como DB Browser for SQLite para inspecionar as tabelas.
- Sempre mantenha a sessao `uvicorn` em execucao enquanto o front-end consumir a API.
