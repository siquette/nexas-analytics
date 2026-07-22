"""
services/ingestor.py — Lê o XLSX, valida e insere no banco.

COLUMN_MAP v2: nomes simplificados sem acentos + nova coluna PER_RELATIVO %
"""

import logging
from pathlib import Path
from datetime import date

import pandas as pd
from sqlalchemy.orm import Session

from backend.models.lift import Onda, LiftResultado

logger = logging.getLogger(__name__)

COLUMN_MAP = {
    "ASSUNTO_COLUNA":        "assunto_coluna",
    "PERGUNTA_COLUNA":       "pergunta_coluna",
    "CATEGORIA_COLUNA":      "categoria_coluna",
    "ASSUNTO_LINHA":         "assunto_linha",
    "PERGUNTA_LINHA":        "pergunta_linha",
    "CATEGORIA_LINHA":       "categoria_linha",
    "LIFT":                  "lift",
    "BASE_PERGUNTA_COMUM":   "base_pergunta_comum",
    "BASE_CAT_COLUNA":       "base_cat_coluna",
    "BASE_CAT_LINHA":        "base_cat_linha",
    "BASE_CAT_COMUM":        "base_cat_comum",
    "SCORE":                 "score_relevancia",
    "SCORE_ABSOLUTO":        "score_absoluto",
    "DIRECAO":               "direcao",
    "CATEGORIA_DIRECAO":     "categoria_direcao",
    "RANK":                  "rank_global",
    "PERCENTIL":             "percentil_relevancia",
    "RANKING_FINAL_DRIVERS": "ranking_final",
    "PER_RELATIVO %":        "per_relativo",
}

REQUIRED_COLUMNS = set(COLUMN_MAP.keys())


class IngestorError(Exception):
    pass


class IngestorResult:
    def __init__(self, onda_codigo: str):
        self.onda_codigo = onda_codigo
        self.total_inseridos = 0
        self.warnings: list[str] = []
        self.success = False

    def __repr__(self):
        return f"<Ingestão {self.onda_codigo}: {'OK' if self.success else 'FALHOU'} | {self.total_inseridos} registros>"


def validate_xlsx(df: pd.DataFrame) -> list[str]:
    warnings = []
    faltando = REQUIRED_COLUMNS - set(df.columns)
    if faltando:
        raise IngestorError(f"Colunas ausentes no XLSX: {faltando}")
    extras = set(df.columns) - REQUIRED_COLUMNS
    if extras:
        warnings.append(f"Colunas extras ignoradas: {extras}")
    if len(df) == 0:
        raise IngestorError("O XLSX não contém dados (0 linhas).")
    if not pd.api.types.is_numeric_dtype(df["LIFT"]):
        raise IngestorError("Coluna LIFT não é numérica.")
    key_cols = ["ASSUNTO_COLUNA","PERGUNTA_COLUNA","CATEGORIA_COLUNA","ASSUNTO_LINHA","PERGUNTA_LINHA","CATEGORIA_LINHA"]
    for col in key_cols:
        nulos = df[col].isna().sum()
        if nulos > 0:
            warnings.append(f"{col}: {nulos} valores nulos.")
    return warnings


def ingest_xlsx(
    db: Session,
    filepath: str | Path,
    onda_codigo: str,
    onda_descricao: str | None = None,
    data_pesquisa: date | None = None,
    sheet_name: str = "BASE_LIFT",
) -> IngestorResult:
    result = IngestorResult(onda_codigo)
    filepath = Path(filepath)

    if not filepath.exists():
        raise IngestorError(f"Arquivo não encontrado: {filepath}")

    logger.info(f"Lendo arquivo: {filepath}")

    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name)
    except Exception as e:
        raise IngestorError(f"Erro ao ler o XLSX: {e}")

    logger.info(f"Arquivo lido: {len(df)} linhas")

    result.warnings = validate_xlsx(df)
    for w in result.warnings:
        logger.warning(w)

    onda_existente = db.query(Onda).filter_by(codigo=onda_codigo).first()
    if onda_existente:
        raise IngestorError(f"Onda '{onda_codigo}' já existe. Delete antes de reingerir.")

    onda = Onda(
        codigo=onda_codigo,
        descricao=onda_descricao,
        data_pesquisa=data_pesquisa,
        total_registros=len(df),
        arquivo_origem=filepath.name,
    )
    db.add(onda)
    db.flush()

    df_renamed = df[list(COLUMN_MAP.keys())].rename(columns=COLUMN_MAP)
    df_renamed["onda_id"] = onda.id

    int_cols = ["base_pergunta_comum","base_cat_coluna","base_cat_linha","base_cat_comum","rank_global"]
    for col in int_cols:
        if col in df_renamed.columns:
            df_renamed[col] = df_renamed[col].where(df_renamed[col].notna(), None)

    if "per_relativo" in df_renamed.columns:
        df_renamed["per_relativo"] = df_renamed["per_relativo"].where(df_renamed["per_relativo"].notna(), None)

    records = df_renamed.to_dict(orient="records")
    chunk_size = 5000
    for i in range(0, len(records), chunk_size):
        db.bulk_insert_mappings(LiftResultado, records[i:i+chunk_size])
        logger.info(f"  Inseridos {min(i+chunk_size, len(records))}/{len(records)}")

    db.commit()
    result.total_inseridos = len(records)
    result.success = True
    logger.info(f"Ingestão concluída: {result}")
    return result
