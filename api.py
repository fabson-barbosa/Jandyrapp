from __future__ import annotations

from decimal import Decimal
from typing import Iterator, List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from db_setup import (
    Alergeno,
    Base,
    BdCardapioSemanal,
    BdIngrediente,
    BdPratoIngrediente,
    BdRefeicao,
    DB_PATH,
    Macronutriente,
    criar_engine,
)

engine = criar_engine()
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

ENDPOINTS_OVERVIEW = [
    {
        "secao": "Ingredientes",
        "descricao": "Gerencia os itens básicos utilizados nas refeições.",
        "rotas": [
            {
                "metodo": "GET",
                "caminho": "/ingredientes",
                "descricao": "Lista todos os ingredientes cadastrados ordenados por nome.",
                "resposta": "Lista[IngredienteRead]",
            },
            {
                "metodo": "POST",
                "caminho": "/ingredientes",
                "descricao": "Cria um novo ingrediente. Todos os campos são obrigatórios.",
                "payload": "IngredienteCreate",
                "resposta": "IngredienteRead",
                "status": 201,
            },
        ],
    },
    {
        "secao": "Refeições",
        "descricao": "Permite montar pratos com ingredientes existentes e registrar no cardápio.",
        "rotas": [
            {
                "metodo": "GET",
                "caminho": "/refeicoes",
                "descricao": "Lista refeições incluindo ingredientes e agenda semanal.",
                "resposta": "Lista[RefeicaoRead]",
            },
            {
                "metodo": "POST",
                "caminho": "/refeicoes",
                "descricao": "Registra uma refeição nova informando os ingredientes existentes e, opcionalmente, dias/turnos.",
                "payload": "RefeicaoCreate",
                "resposta": "RefeicaoRead",
                "status": 201,
            },
        ],
    },
    {
        "secao": "Cardápio Semanal",
        "descricao": "Consulta o planejamento de refeições conforme agenda.",
        "rotas": [
            {
                "metodo": "GET",
                "caminho": "/cardapio",
                "descricao": "Retorna o cardápio semanal. Parâmetros opcionais filtram por dia e tipo de refeição.",
                "query_params": {
                    "dia": "Opcional. Dia da semana (ex.: Segunda).",
                    "tipo": "Opcional. Categoria (ex.: Almoço).",
                },
                "resposta": "Lista[CardapioRead]",
            }
        ],
    },
]

app = FastAPI(
    title="Cardápio Semanal API",
    version="1.0.0",
    description="API para gestão de ingredientes, refeições e cardápio semanal.",
)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class IngredienteBase(BaseModel):
    nome: str
    valor_energetico: int
    alergenico: Alergeno
    macronutriente: Macronutriente
    quantidade: Decimal = Field(..., ge=Decimal("0"), max_digits=10, decimal_places=2)
    unidade_medida: str
    preco_medio: Decimal = Field(..., ge=Decimal("0"), max_digits=10, decimal_places=2)

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = {Decimal: lambda v: float(v)}


class IngredienteCreate(IngredienteBase):
    pass


class IngredienteRead(IngredienteBase):
    id_ingrediente: int


class PratoIngredienteCreate(BaseModel):
    id_ingrediente: int
    quantidade: Decimal = Field(..., ge=Decimal("0"), max_digits=10, decimal_places=2)
    unidade_medida: str

    class Config:
        orm_mode = True
        json_encoders = {Decimal: lambda v: float(v)}


class PratoIngredienteRead(BaseModel):
    id_prato_ingrediente: int
    quantidade: Decimal = Field(..., ge=Decimal("0"), max_digits=10, decimal_places=2)
    unidade_medida: str
    ingrediente: IngredienteRead

    class Config:
        orm_mode = True
        json_encoders = {Decimal: lambda v: float(v)}


class CardapioEntrada(BaseModel):
    dia_da_semana: str
    tipo_refeicao: str


class CardapioRead(BaseModel):
    id_cardapio_semanal: int
    dia_da_semana: str
    tipo_refeicao: str
    refeicao: "RefeicaoResumo"

    class Config:
        orm_mode = True


class RefeicaoCreate(BaseModel):
    nome_prato: str
    descricao: Optional[str] = None
    ingredientes: List[PratoIngredienteCreate]
    cardapio: Optional[List[CardapioEntrada]] = None


class RefeicaoResumo(BaseModel):
    id_refeicao: int
    nome_prato: str
    descricao: Optional[str]

    class Config:
        orm_mode = True


class RefeicaoRead(RefeicaoResumo):
    ingredientes: List[PratoIngredienteRead]
    cardapio: List[CardapioRead]


CardapioRead.update_forward_refs()
RefeicaoRead.update_forward_refs()


@app.get("/", tags=["Meta"])
async def raiz() -> dict[str, object]:
    """Apresenta um guia rápido de integração para o front-end."""
    return {
        "titulo": "Cardápio Semanal API",
        "versao": app.version,
        "ambiente": {
            "banco_dados": f"sqlite:///{DB_PATH.name}",
        },
        "como_usar": [
            {
                "etapa": 1,
                "descricao": "Crie ingredientes básicos via POST /ingredientes.",
            },
            {
                "etapa": 2,
                "descricao": "Monte refeições com POST /refeicoes reutilizando os ids de ingredientes.",
            },
            {
                "etapa": 3,
                "descricao": "Consulte o cardápio preparado em GET /cardapio aplicando filtros quando necessário.",
            },
        ],
        "recursos": ENDPOINTS_OVERVIEW,
        "documentacao": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json",
        },
        "observacoes": [
            "Envie JSON com chaves em snake_case conforme os esquemas.",
            "Valores numéricos suportam duas casas decimais e não aceitam negativos.",
        ],
    }


@app.get("/ingredientes", response_model=List[IngredienteRead])
async def listar_ingredientes(db: Session = Depends(get_db)) -> List[BdIngrediente]:
    stmt = select(BdIngrediente).order_by(BdIngrediente.nome)
    return db.execute(stmt).scalars().all()


@app.post("/ingredientes", response_model=IngredienteRead, status_code=status.HTTP_201_CREATED)
async def criar_ingrediente(payload: IngredienteCreate, db: Session = Depends(get_db)) -> BdIngrediente:
    existente = db.execute(select(BdIngrediente).filter_by(nome=payload.nome)).scalars().first()
    if existente:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ingrediente já cadastrado")

    ingrediente = BdIngrediente(
        nome=payload.nome,
        valor_energetico=payload.valor_energetico,
        alergenico=Alergeno(payload.alergenico),
        macronutriente=Macronutriente(payload.macronutriente),
        quantidade=Decimal(str(payload.quantidade)),
        unidade_medida=payload.unidade_medida,
        preco_medio=Decimal(str(payload.preco_medio)),
    )
    db.add(ingrediente)
    db.commit()
    db.refresh(ingrediente)
    return ingrediente


@app.get("/refeicoes", response_model=List[RefeicaoRead])
async def listar_refeicoes(db: Session = Depends(get_db)) -> List[BdRefeicao]:
    stmt = (
        select(BdRefeicao)
        .options(
            selectinload(BdRefeicao.ingredientes).selectinload(BdPratoIngrediente.ingrediente),
            selectinload(BdRefeicao.cardapios),
        )
        .order_by(BdRefeicao.nome_prato)
    )
    return db.execute(stmt).scalars().unique().all()


@app.post("/refeicoes", response_model=RefeicaoRead, status_code=status.HTTP_201_CREATED)
async def criar_refeicao(payload: RefeicaoCreate, db: Session = Depends(get_db)) -> BdRefeicao:
    pratos = db.execute(select(BdRefeicao).filter_by(nome_prato=payload.nome_prato)).scalars().first()
    if pratos:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Refeição já cadastrada")

    if not payload.ingredientes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe ao menos um ingrediente")

    refeicao = BdRefeicao(nome_prato=payload.nome_prato, descricao=payload.descricao)
    db.add(refeicao)
    db.flush()

    for item in payload.ingredientes:
        ingrediente = db.get(BdIngrediente, item.id_ingrediente)
        if not ingrediente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ingrediente id {item.id_ingrediente} não encontrado",
            )
        prato_ingrediente = BdPratoIngrediente(
            refeicao=refeicao,
            ingrediente=ingrediente,
            quantidade=Decimal(str(item.quantidade)),
            unidade_medida=item.unidade_medida,
        )
        db.add(prato_ingrediente)

    if payload.cardapio:
        for dia in payload.cardapio:
            registro = BdCardapioSemanal(
                refeicao=refeicao,
                dia_da_semana=dia.dia_da_semana,
                tipo_refeicao=dia.tipo_refeicao,
            )
            db.add(registro)

    db.commit()

    refeicao_completa = (
        db.execute(
            select(BdRefeicao)
            .options(
                selectinload(BdRefeicao.ingredientes).selectinload(BdPratoIngrediente.ingrediente),
                selectinload(BdRefeicao.cardapios),
            )
            .filter(BdRefeicao.id_refeicao == refeicao.id_refeicao)
        )
        .scalars()
        .first()
    )

    return refeicao_completa


@app.get("/cardapio", response_model=List[CardapioRead])
async def listar_cardapio(
    dia: Optional[str] = None,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
) -> List[BdCardapioSemanal]:
    stmt = select(BdCardapioSemanal).options(selectinload(BdCardapioSemanal.refeicao)).order_by(
        BdCardapioSemanal.dia_da_semana, BdCardapioSemanal.tipo_refeicao
    )

    if dia:
        stmt = stmt.filter(BdCardapioSemanal.dia_da_semana == dia)
    if tipo:
        stmt = stmt.filter(BdCardapioSemanal.tipo_refeicao == tipo)

    return db.execute(stmt).scalars().all()
