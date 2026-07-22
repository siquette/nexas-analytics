"""
models/lift.py — Modelos SQLAlchemy.
"""

from sqlalchemy import Column, Integer, String, Text, Numeric, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from backend.database import Base


class Onda(Base):
    __tablename__ = "ondas"

    id               = Column(Integer, primary_key=True, index=True)
    codigo           = Column(String(50), unique=True, nullable=False)
    descricao        = Column(Text)
    data_pesquisa    = Column(Date)
    data_ingestao    = Column(DateTime, server_default=func.now())
    total_registros  = Column(Integer)
    arquivo_origem   = Column(String(500))

    resultados = relationship("LiftResultado", back_populates="onda", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Onda {self.codigo} ({self.total_registros} registros)>"


class LiftResultado(Base):
    __tablename__ = "lift_resultados"

    id       = Column(Integer, primary_key=True, index=True)
    onda_id  = Column(Integer, ForeignKey("ondas.id", ondelete="CASCADE"), nullable=False)
    onda     = relationship("Onda", back_populates="resultados")

    # Cross 1 (coluna)
    assunto_coluna   = Column(String(200), nullable=False)
    pergunta_coluna  = Column(Text, nullable=False)
    categoria_coluna = Column(String(300), nullable=False)

    # Cross 2 (linha)
    assunto_linha   = Column(String(200), nullable=False)
    pergunta_linha  = Column(Text, nullable=False)
    categoria_linha = Column(String(300), nullable=False)

    # Métricas
    lift                 = Column(Numeric(12, 6))
    base_pergunta_comum  = Column(Integer)
    base_cat_coluna      = Column(Integer)
    base_cat_linha       = Column(Integer)
    base_cat_comum       = Column(Integer)
    score_relevancia     = Column(Numeric(12, 6))
    score_absoluto       = Column(Numeric(12, 6))
    direcao              = Column(String(50))
    categoria_direcao    = Column(String(100))
    rank_global          = Column(Integer)
    percentil_relevancia = Column(Numeric(8, 6))
    ranking_final        = Column(String(100))
    per_relativo         = Column(Numeric(8, 4), nullable=True)

    def __repr__(self):
        return f"<Lift {self.assunto_coluna}|{self.categoria_coluna} → {self.categoria_linha}>"
