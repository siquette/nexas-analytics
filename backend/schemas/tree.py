"""
schemas/tree.py — Schemas Pydantic (contrato da API).
"""

from __future__ import annotations
from pydantic import BaseModel


class LeafMetrics(BaseModel):
    lift:              float
    score_nexas:       float
    relevancia:        float
    direcao:           str
    categoria_direcao: str
    rank_global:       int | None = None
    base_comum:        int | None = None
    per_relativo:      float | None = None


class NodeMetrics(BaseModel):
    avg_score:      float
    min_score:      float = 0
    max_score:      float = 0
    median_score:   float = 0
    std_dev:        float = 0
    avg_relevancia: float
    count:          int
    composition:    dict | None = None


class TreeNode(BaseModel):
    name:     str
    nivel:    str
    leaf:     bool = False
    metrics:  LeafMetrics | NodeMetrics | None = None
    value:    float | None = None
    children: list[TreeNode] = []


class TreeContexto(BaseModel):
    assunto_coluna:  str
    pergunta_coluna: str
    onda:            str
    direcao_filtro:  str | None = None


class TreeResponse(BaseModel):
    root:     str
    contexto: TreeContexto
    tree:     TreeNode


class OndaResponse(BaseModel):
    codigo:          str
    descricao:       str | None = None
    data_pesquisa:   str | None = None
    total_registros: int | None = None


class FiltrosPerguntasResponse(BaseModel):
    assunto:   str
    perguntas: list[str]


class FiltrosCategoriasResponse(BaseModel):
    pergunta:   str
    categorias: list[str]


class MetricasResumo(BaseModel):
    total_cruzamentos:    int
    total_drivers:        int
    total_anti_drivers:   int
    total_baixa_relevancia: int
    top_score:            float
    top_categoria:        str
    distribuicao_direcao: dict[str, int]


class FiltrosResponse(BaseModel):
    assuntos:   list[str]
    perguntas:  dict[str, list[str]]
    categorias: dict[str, list[str]]
