"""
schemas/tree.py — Define o formato exato do JSON que a API retorna.

Isso é o CONTRATO entre backend e frontend.
Se o backend retornar algo diferente, o Pydantic dá erro.
Se o frontend espera algo diferente, a gente muda aqui.

v2: adicionado per_relativo no LeafMetrics
"""

from __future__ import annotations

from pydantic import BaseModel


# ============================================
# Schemas do dendrograma / sunburst
# ============================================

class LeafMetrics(BaseModel):
    """Métricas de um nó folha (CATEGORIA_LINHA) — o nível mais profundo."""
    lift: float
    score_nexas: float
    relevancia: float
    direcao: str
    categoria_direcao: str
    rank_global: int | None = None
    base_comum: int | None = None
    per_relativo: float | None = None      # PER_RELATIVO % — percentual relativo


class NodeMetrics(BaseModel):
    avg_score: float
    min_score: float = 0
    max_score: float = 0
    median_score: float = 0
    std_dev: float = 0
    avg_relevancia: float
    count: int
    composition: dict | None = None


class TreeNode(BaseModel):
    """
    Nó da árvore hierárquica — usado tanto no dendrograma quanto no sunburst.

    Níveis:
        0 (root)  → name = ASSUNTO_COLUNA | PERGUNTA_COLUNA
        1         → name = CATEGORIA_COLUNA
        2         → name = ASSUNTO_LINHA
        3         → name = PERGUNTA_LINHA
        4 (leaf)  → name = CATEGORIA_LINHA
    """
    name: str
    nivel: str
    leaf: bool = False
    metrics: LeafMetrics | NodeMetrics | None = None
    value: float | None = None
    children: list[TreeNode] = []


class TreeResponse(BaseModel):
    """Resposta completa do endpoint /api/tree."""
    root: str
    contexto: TreeContexto
    tree: TreeNode


class TreeContexto(BaseModel):
    """Informações contextuais para o texto explicativo no frontend."""
    assunto_coluna: str
    pergunta_coluna: str
    onda: str
    direcao_filtro: str | None = None


# ============================================
# Schemas de filtros
# ============================================

class OndaResponse(BaseModel):
    codigo: str
    descricao: str | None = None
    data_pesquisa: str | None = None
    total_registros: int | None = None


class FiltrosResponse(BaseModel):
    assuntos: list[str]
    perguntas: dict[str, list[str]]
    categorias: dict[str, list[str]]


class FiltrosPerguntasResponse(BaseModel):
    assunto: str
    perguntas: list[str]


class FiltrosCategoriasResponse(BaseModel):
    pergunta: str
    categorias: list[str]


# ============================================
# Schemas de métricas resumidas
# ============================================

class MetricasResumo(BaseModel):
    total_cruzamentos: int
    total_drivers: int
    total_anti_drivers: int
    total_baixa_relevancia: int
    top_score: float
    top_categoria: str
    distribuicao_direcao: dict[str, int]
