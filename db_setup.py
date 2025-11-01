from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path

from sqlalchemy import CheckConstraint, Enum as SqlEnum, ForeignKey, Integer, Numeric, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship


DB_PATH = Path(__file__).with_name("bd_teste.sqlite")


class Base(DeclarativeBase):
    pass


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
