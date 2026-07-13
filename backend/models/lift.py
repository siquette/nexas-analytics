"""
models/lift.py — Modelos SQLAlchemy das tabelas do banco.

Cada classe aqui é um espelho de uma tabela no banco.
O SQLAlchemy traduz operações Python em SQL automaticamente.

Os nomes das colunas seguem EXATAMENTE os nomes do XLSX,
convertidos para snake_case. Isso evita mapeamentos confusos.

v2: adicionado campo per_relativo (PER_RELATIVO % do XLSX novo)
"""

from sqlalchemy import (
    Column, Integer, String, Text, Numeric,
    Date, DateTime, ForeignKey, func
)
from sqlalchemy.orm import relationship

from backend.database import Base


class Onda(Base):
    """
    Metadados de cada onda de pesquisa.
    Cada XLSX ingerido vira um registro aqui.
    """
    __tablename__ = "ondas"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False)
    descricao = Column(Text)
    data_pesquisa = Column(Date)
    data_ingestao = Column(DateTime, server_default=func.now())
    total_registros = Column(Integer)
    arquivo_origem = Column(String(500))

    resultados = relationship("LiftResultado", back_populates="onda", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Onda {self.codigo} ({self.total_registros} registros)>"


class LiftResultado(Base):
    """
    Resultado do Lift Condicional entre dois cruzamentos.

    Cada linha representa: dado que o respondente está na CATEGORIA_COLUNA
    de uma PERGUNTA_COLUNA (cross 1), qual a força de associação com
    a CATEGORIA_LINHA de uma PERGUNTA_LINHA (cross 2)?
    """
    __tablename__ = "lift_resultados"

    id = Column(Integer, primary_key=True, index=True)

    # FK para onda
    onda_id = Column(Integer, ForeignKey("ondas.id", ondelete="CASCADE"), nullable=False)
    onda = relationship("Onda", back_populates="resultados")

    # --- Cross 1 (coluna) ---
    assunto_coluna = Column(String(200), nullable=False)
    pergunta_coluna = Column(Text, nullable=False)
    categoria_coluna = Column(String(300), nullable=False)

    # --- Cross 2 (linha) ---
    assunto_linha = Column(String(200), nullable=False)
    pergunta_linha = Column(Text, nullable=False)
    categoria_linha = Column(String(300), nullable=False)

    # --- Métricas de associação ---
    lift = Column(Numeric(12, 6))
    base_pergunta_comum = Column(Integer)
    base_cat_coluna = Column(Integer)
    base_cat_linha = Column(Integer)
    base_cat_comum = Column(Integer)

    # --- Scores calculados ---
    score_relevancia = Column(Numeric(12, 6))
    score_absoluto = Column(Numeric(12, 6))

    # --- Classificação ---
    direcao = Column(String(50))
    categoria_direcao = Column(String(100))
    rank_global = Column(Integer)
    percentil_relevancia = Column(Numeric(8, 6))
    ranking_final = Column(String(100))

    # --- Percentual relativo (novo — PER_RELATIVO % do XLSX v2) ---
    per_relativo = Column(Numeric(8, 4), nullable=True)

    def __repr__(self):
        return (
            f"<Lift {self.assunto_coluna}|{self.categoria_coluna} "
            f"→ {self.categoria_linha} = {self.lift}>"
        )
