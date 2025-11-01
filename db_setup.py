from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import CheckConstraint, Enum as SqlEnum, ForeignKey, Integer, Numeric, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


DB_PATH = Path(__file__).with_name("bd_teste.sqlite")
ALUNO_KEY_PATH = Path(__file__).with_name("aluno.key")


class Base(DeclarativeBase):
    pass


def carregar_chave_encriptacao() -> bytes:
    chave_env = os.getenv("ALUNO_ENCRYPTION_KEY")
    if chave_env:
        try:
            chave_bytes = chave_env.encode("utf-8")
            Fernet(chave_bytes)
            return chave_bytes
        except (ValueError, TypeError):
            raise ValueError("ALUNO_ENCRYPTION_KEY inválida. Forneça uma chave Fernet válida.") from None

    if ALUNO_KEY_PATH.exists():
        chave_bytes = ALUNO_KEY_PATH.read_bytes()
        Fernet(chave_bytes)
        return chave_bytes

    chave = Fernet.generate_key()
    ALUNO_KEY_PATH.write_bytes(chave)
    return chave


FERNET = Fernet(carregar_chave_encriptacao())


class EncryptedString(TypeDecorator[str]):
    """TypeDecorator que criptografa dados sensíveis antes de persistir."""

    impl = String(255)
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect):  # type: ignore[override]
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("EncryptedString espera valores do tipo str")
        token = FERNET.encrypt(value.encode("utf-8"))
        return token.decode("utf-8")

    def process_result_value(self, value: str | None, dialect):  # type: ignore[override]
        if value is None:
            return None
        try:
            texto = FERNET.decrypt(value.encode("utf-8"))
            return texto.decode("utf-8")
        except InvalidToken:
            return value


class Alergeno(Enum):
    GLUTEN = "Glúten"
    LACTOSE = "Lactose"
    OVO = "Ovo"
    SOJA = "Soja"
    AMENDOIM = "Amendoim"
    CASTANHAS = "Castanhas"
    FRUTOS_DO_MAR = "Frutos do mar"


class Macronutriente(Enum):
    CARBOIDRATOS = "Carboidratos"
    PROTEINAS = "Proteínas"
    LIPIDIOS = "Lipídios"


class BdIngrediente(Base):
    __tablename__ = "bd_ingredientes"

    id_ingrediente: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    valor_energetico: Mapped[int] = mapped_column(Integer, nullable=False)
    alergenico: Mapped[Alergeno] = mapped_column(SqlEnum(Alergeno, name="alergenico_enum"), nullable=False)
    macronutriente: Mapped[Macronutriente] = mapped_column(SqlEnum(Macronutriente, name="macronutriente_enum"), nullable=False)
    quantidade: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unidade_medida: Mapped[str] = mapped_column(String(20), nullable=False)
    preco_medio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    pratos: Mapped[list[BdPratoIngrediente]] = relationship(back_populates="ingrediente", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("valor_energetico >= 0", name="ck_valor_energetico_nao_negativo"),
        CheckConstraint("quantidade >= 0", name="ck_quantidade_nao_negativa"),
        CheckConstraint("preco_medio >= 0", name="ck_preco_medio_nao_negativo"),
    )


class BdRefeicao(Base):
    __tablename__ = "bd_refeicoes"

    id_refeicao: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome_prato: Mapped[str] = mapped_column(String(120), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)

    ingredientes: Mapped[list[BdPratoIngrediente]] = relationship(back_populates="refeicao", cascade="all, delete-orphan")
    cardapios: Mapped[list[BdCardapioSemanal]] = relationship(back_populates="refeicao", cascade="all, delete-orphan")


class BdPratoIngrediente(Base):
    __tablename__ = "bd_pratos_ingredientes"

    id_prato_ingrediente: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_refeicao: Mapped[int] = mapped_column(ForeignKey("bd_refeicoes.id_refeicao", ondelete="CASCADE"), nullable=False)
    id_ingrediente: Mapped[int] = mapped_column(ForeignKey("bd_ingredientes.id_ingrediente", ondelete="CASCADE"), nullable=False)
    quantidade: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unidade_medida: Mapped[str] = mapped_column(String(20), nullable=False)

    refeicao: Mapped[BdRefeicao] = relationship(back_populates="ingredientes")
    ingrediente: Mapped[BdIngrediente] = relationship(back_populates="pratos")

    __table_args__ = (
        CheckConstraint("quantidade >= 0", name="ck_prato_ingrediente_quantidade_nao_negativa"),
    )


class BdCardapioSemanal(Base):
    __tablename__ = "bd_cardapio_semanal"

    id_cardapio_semanal: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_refeicao: Mapped[int] = mapped_column(ForeignKey("bd_refeicoes.id_refeicao", ondelete="CASCADE"), nullable=False)
    dia_da_semana: Mapped[str] = mapped_column(String(20), nullable=False)
    tipo_refeicao: Mapped[str] = mapped_column(String(40), nullable=False)

    refeicao: Mapped[BdRefeicao] = relationship(back_populates="cardapios")


class BdTurma(Base):
    __tablename__ = "bd_turmas"

    id_turma: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome_turma: Mapped[str | None] = mapped_column(String(60), nullable=True)
    serie: Mapped[str] = mapped_column(String(40), nullable=False)
    periodo: Mapped[str] = mapped_column(String(40), nullable=False)

    alunos: Mapped[list["BdAluno"]] = relationship(back_populates="turma")

    __table_args__ = (
        CheckConstraint("length(serie) > 0", name="ck_turma_serie_nao_vazia"),
        CheckConstraint("length(periodo) > 0", name="ck_turma_periodo_nao_vazio"),
    )


class BdAluno(Base):
    __tablename__ = "bd_alunos"

    id_aluno: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(EncryptedString(255), nullable=False)
    ra: Mapped[str] = mapped_column(EncryptedString(255), nullable=False)
    ra_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    serie: Mapped[str] = mapped_column(String(40), nullable=False)
    periodo: Mapped[str] = mapped_column(String(40), nullable=False)
    observacoes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    turma_id: Mapped[int | None] = mapped_column(ForeignKey("bd_turmas.id_turma", ondelete="SET NULL"), nullable=True)

    turma: Mapped[BdTurma | None] = relationship(back_populates="alunos")
    alergias: Mapped[list["BdAlunoAlergia"]] = relationship(back_populates="aluno", cascade="all, delete-orphan")
    hobbies: Mapped[list["BdAlunoHobbie"]] = relationship(back_populates="aluno", cascade="all, delete-orphan")
    dificuldades: Mapped[list["BdAlunoDificuldade"]] = relationship(back_populates="aluno", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("length(serie) > 0", name="ck_aluno_serie_nao_vazia"),
        CheckConstraint("length(periodo) > 0", name="ck_aluno_periodo_nao_vazio"),
        CheckConstraint("length(ra_hash) = 64", name="ck_aluno_ra_hash_tamanho"),
    )


class BdAlunoAlergia(Base):
    __tablename__ = "bd_alunos_alergenicos"

    id_alergia: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_aluno: Mapped[int] = mapped_column(ForeignKey("bd_alunos.id_aluno", ondelete="CASCADE"), nullable=False)
    descricao: Mapped[str] = mapped_column(String(120), nullable=False)

    aluno: Mapped[BdAluno] = relationship(back_populates="alergias")


class BdAlunoHobbie(Base):
    __tablename__ = "bd_alunos_hobbies"

    id_hobbie: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_aluno: Mapped[int] = mapped_column(ForeignKey("bd_alunos.id_aluno", ondelete="CASCADE"), nullable=False)
    descricao: Mapped[str] = mapped_column(String(120), nullable=False)

    aluno: Mapped[BdAluno] = relationship(back_populates="hobbies")


class BdAlunoDificuldade(Base):
    __tablename__ = "bd_alunos_dificuldades"

    id_dificuldade: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_aluno: Mapped[int] = mapped_column(ForeignKey("bd_alunos.id_aluno", ondelete="CASCADE"), nullable=False)
    descricao: Mapped[str] = mapped_column(String(180), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    aluno: Mapped[BdAluno] = relationship(back_populates="dificuldades")

    __table_args__ = (
        CheckConstraint("ordem >= 1", name="ck_dificuldade_ordem_minima"),
    )


@dataclass(slots=True)
class NovaRefeicao:
    nome_prato: str
    descricao: str
    ingredientes: list[tuple["NovoIngrediente", float, str]]


@dataclass(slots=True)
class NovoIngrediente:
    nome: str
    valor_energetico: int
    alergenico: Alergeno
    macronutriente: Macronutriente
    quantidade: float
    unidade_medida: str
    preco_medio: float


@dataclass(slots=True)
class NovoAluno:
    nome: str
    ra: str
    serie: str
    periodo: str
    alergias: list[str] = field(default_factory=list)
    hobbies: list[str] = field(default_factory=list)
    dificuldades: list[str] = field(default_factory=list)
    observacoes: str | None = None
    nome_turma: str | None = None


def _hash_texto(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


def _obter_ou_criar_turma(session: Session, serie: str, periodo: str, nome_turma: str | None) -> BdTurma:
    consulta = session.query(BdTurma).filter(BdTurma.serie == serie, BdTurma.periodo == periodo)
    if nome_turma is None:
        consulta = consulta.filter(BdTurma.nome_turma.is_(None))
    else:
        consulta = consulta.filter(BdTurma.nome_turma == nome_turma)

    turma = consulta.first()
    if turma is None:
        turma = BdTurma(nome_turma=nome_turma, serie=serie, periodo=periodo)
        session.add(turma)
        session.flush()

    return turma


def cadastrar_aluno(engine, aluno: NovoAluno) -> None:
    with Session(engine) as session:
        turma = _obter_ou_criar_turma(session, aluno.serie, aluno.periodo, aluno.nome_turma)

        ra_hash = _hash_texto(aluno.ra)
        existente = session.query(BdAluno).filter(BdAluno.ra_hash == ra_hash).first()
        if existente:
            raise ValueError("Aluno com este RA já está cadastrado.")

        novo_aluno = BdAluno(
            nome=aluno.nome,
            ra=aluno.ra,
            ra_hash=ra_hash,
            serie=aluno.serie,
            periodo=aluno.periodo,
            observacoes=aluno.observacoes,
            turma=turma,
        )
        session.add(novo_aluno)
        session.flush()

        for descricao in aluno.alergias:
            texto = descricao.strip()
            if texto:
                session.add(BdAlunoAlergia(aluno=novo_aluno, descricao=texto))

        for descricao in aluno.hobbies:
            texto = descricao.strip()
            if texto:
                session.add(BdAlunoHobbie(aluno=novo_aluno, descricao=texto))

        for indice, descricao in enumerate(aluno.dificuldades, start=1):
            texto = descricao.strip()
            if texto:
                session.add(BdAlunoDificuldade(aluno=novo_aluno, descricao=texto, ordem=indice))

        session.commit()


def criar_engine(echo: bool = False):
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=echo, future=True)
    return engine


def criar_tabelas(engine) -> None:
    Base.metadata.create_all(engine)


def preencher_dados_exemplo(engine) -> None:
    with Session(engine) as session:
        aveia = BdIngrediente(
            nome="Aveia",
            valor_energetico=389,
            alergenico=Alergeno.GLUTEN,
            macronutriente=Macronutriente.CARBOIDRATOS,
            quantidade=Decimal("100"),
            unidade_medida="g",
            preco_medio=Decimal("8.50"),
        )
        leite = BdIngrediente(
            nome="Leite integral",
            valor_energetico=61,
            alergenico=Alergeno.LACTOSE,
            macronutriente=Macronutriente.PROTEINAS,
            quantidade=Decimal("200"),
            unidade_medida="ml",
            preco_medio=Decimal("4.20"),
        )

        mingau = BdRefeicao(nome_prato="Mingau de aveia", descricao="Aveia cozida em leite integral")

        session.add_all([aveia, leite, mingau])
        session.flush()

        session.add_all(
            [
                BdPratoIngrediente(
                    refeicao=mingau,
                    ingrediente=aveia,
                    quantidade=Decimal("40"),
                    unidade_medida="g",
                ),
                BdPratoIngrediente(
                    refeicao=mingau,
                    ingrediente=leite,
                    quantidade=Decimal("200"),
                    unidade_medida="ml",
                ),
            ]
        )

        session.add(
            BdCardapioSemanal(
                refeicao=mingau,
                dia_da_semana="Segunda",
                tipo_refeicao="Café da manhã",
            )
        )

        turma = BdTurma(nome_turma="Turma A", serie="5º ano", periodo="Matutino")
        session.add(turma)
        session.flush()

        aluno = BdAluno(
            nome="Ana Souza",
            ra="2025-001",
            ra_hash=_hash_texto("2025-001"),
            serie=turma.serie,
            periodo=turma.periodo,
            observacoes="Possui alergia a leite. Gosta de atividades artisticas.",
            turma=turma,
        )
        session.add(aluno)
        session.flush()

        session.add_all(
            [
                BdAlunoAlergia(aluno=aluno, descricao="Leite"),
                BdAlunoHobbie(aluno=aluno, descricao="Desenho"),
                BdAlunoHobbie(aluno=aluno, descricao="Futebol"),
                BdAlunoDificuldade(aluno=aluno, descricao="Foco e concentração", ordem=1),
                BdAlunoDificuldade(aluno=aluno, descricao="Matemática", ordem=2),
            ]
        )

        session.commit()


def criar_cardapio(engine, refeicao: NovaRefeicao, agenda: list[tuple[str, str]]) -> None:
    with Session(engine) as session:
        ingredientes_bd: dict[str, BdIngrediente] = {}

        nomes = {ingr.nome for ingr, _, _ in refeicao.ingredientes}
        if nomes:
            existentes = (
                session.query(BdIngrediente)
                .filter(BdIngrediente.nome.in_(nomes))
                .all()
            )
            ingredientes_bd.update({ing.nome: ing for ing in existentes})

        for ingr, _, _ in refeicao.ingredientes:
            if ingr.nome not in ingredientes_bd:
                novo = BdIngrediente(
                    nome=ingr.nome,
                    valor_energetico=ingr.valor_energetico,
                    alergenico=ingr.alergenico,
                    macronutriente=ingr.macronutriente,
                    quantidade=Decimal(str(ingr.quantidade)),
                    unidade_medida=ingr.unidade_medida,
                    preco_medio=Decimal(str(ingr.preco_medio)),
                )
                session.add(novo)
                ingredientes_bd[ingr.nome] = novo

        prato = BdRefeicao(nome_prato=refeicao.nome_prato, descricao=refeicao.descricao)
        session.add(prato)
        session.flush()

        for ingr, qtd, unidade in refeicao.ingredientes:
            bd_ingr = ingredientes_bd[ingr.nome]
            session.add(
                BdPratoIngrediente(
                    refeicao=prato,
                    ingrediente=bd_ingr,
                    quantidade=Decimal(str(qtd)),
                    unidade_medida=unidade,
                )
            )

        for dia, tipo in agenda:
            session.add(BdCardapioSemanal(refeicao=prato, dia_da_semana=dia, tipo_refeicao=tipo))

        session.commit()


def main() -> None:
    engine = criar_engine()
    criar_tabelas(engine)

    with Session(engine) as session:
        tem_dados = session.query(BdIngrediente.id_ingrediente).first() is not None

    if not tem_dados:
        preencher_dados_exemplo(engine)


if __name__ == "__main__":
    main()
