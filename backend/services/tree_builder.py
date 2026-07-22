"""
services/tree_builder.py — Transforma a tabela flat em árvore hierárquica.

A hierarquia padrão (sem filtro de categoria_coluna) é:
    Nível 0 (root):  ASSUNTO_COLUNA | PERGUNTA_COLUNA
    Nível 1:         CATEGORIA_COLUNA
    Nível 2:         ASSUNTO_LINHA
    Nível 3:         PERGUNTA_LINHA
    Nível 4 (leaf):  CATEGORIA_LINHA

Quando categoria_coluna é informada, a árvore começa no nível 2:
    Nível 0 (root):  CATEGORIA_COLUNA
    Nível 1:         ASSUNTO_LINHA
    Nível 2:         PERGUNTA_LINHA
    Nível 3 (leaf):  CATEGORIA_LINHA
"""

import logging
from sqlalchemy.orm import Session

from backend.models.lift import LiftResultado, Onda
from backend.schemas.tree import (
    TreeNode, TreeResponse, TreeContexto,
    LeafMetrics, NodeMetrics,
)

logger = logging.getLogger(__name__)


def build_tree(
    db: Session,
    onda_codigo: str,
    assunto_coluna: str,
    pergunta_coluna: str,
    direcao: str | None = None,
    agregacao: str | None = None,
    categoria_coluna: str | None = None,
) -> TreeResponse:
    onda = db.query(Onda).filter_by(codigo=onda_codigo).first()
    if not onda:
        raise ValueError(f"Onda '{onda_codigo}' não encontrada.")

    query = db.query(LiftResultado).filter(
        LiftResultado.onda_id == onda.id,
        LiftResultado.assunto_coluna == assunto_coluna,
        LiftResultado.pergunta_coluna == pergunta_coluna,
    )

    if categoria_coluna:
        query = query.filter(LiftResultado.categoria_coluna == categoria_coluna)

    if direcao:
        query = query.filter(LiftResultado.direcao == direcao)

    rows = query.all()

    if not rows:
        raise ValueError(
            f"Nenhum resultado para: onda={onda_codigo}, "
            f"assunto={assunto_coluna}, pergunta={pergunta_coluna}"
            + (f", categoria_coluna={categoria_coluna}" if categoria_coluna else "")
        )

    logger.info(f"Construindo árvore: {len(rows)} linhas | categoria_coluna={categoria_coluna}")

    if categoria_coluna:
        tree_node = _build_from_categoria(rows, categoria_coluna)
        root_name = categoria_coluna
    else:
        tree_node = _build_full_tree(rows, assunto_coluna, pergunta_coluna)
        root_name = f"{assunto_coluna} | {pergunta_coluna}"

    return TreeResponse(
        root=root_name,
        contexto=TreeContexto(
            assunto_coluna=assunto_coluna,
            pergunta_coluna=pergunta_coluna,
            onda=onda_codigo,
            direcao_filtro=direcao,
        ),
        tree=tree_node,
    )


def _build_full_tree(rows: list, assunto_coluna: str, pergunta_coluna: str) -> TreeNode:
    """Árvore completa de 4 níveis — comportamento padrão."""
    hierarchy = {}

    for row in rows:
        cat_col = row.categoria_coluna
        ass_lin = row.assunto_linha
        per_lin = row.pergunta_linha

        if cat_col not in hierarchy:
            hierarchy[cat_col] = {}
        if ass_lin not in hierarchy[cat_col]:
            hierarchy[cat_col][ass_lin] = {}
        if per_lin not in hierarchy[cat_col][ass_lin]:
            hierarchy[cat_col][ass_lin][per_lin] = []

        hierarchy[cat_col][ass_lin][per_lin].append(row)

    root_children = []

    for cat_coluna, assuntos in hierarchy.items():
        nivel1_children = _build_nivel1_from_assuntos(assuntos)

        nivel1_node = TreeNode(
            name=cat_coluna,
            nivel="categoria_coluna",
            metrics=_aggregate_metrics_from_nodes(nivel1_children),
            value=_sum_values(nivel1_children),
            children=nivel1_children,
        )
        root_children.append(nivel1_node)

    root_children.sort(
        key=lambda n: n.metrics.avg_score if isinstance(n.metrics, NodeMetrics) else 0,
        reverse=True,
    )

    root_name = f"{assunto_coluna} | {pergunta_coluna}"

    return TreeNode(
        name=root_name,
        nivel="root",
        metrics=_aggregate_metrics_from_nodes(root_children),
        value=_sum_values(root_children),
        children=root_children,
    )


def _build_from_categoria(rows: list, categoria_coluna: str) -> TreeNode:
    """Árvore de 3 níveis com CATEGORIA_COLUNA como root."""
    hierarchy = {}

    for row in rows:
        ass_lin = row.assunto_linha
        per_lin = row.pergunta_linha

        if ass_lin not in hierarchy:
            hierarchy[ass_lin] = {}
        if per_lin not in hierarchy[ass_lin]:
            hierarchy[ass_lin][per_lin] = []

        hierarchy[ass_lin][per_lin].append(row)

    children = _build_nivel1_from_assuntos(hierarchy)

    return TreeNode(
        name=categoria_coluna,
        nivel="categoria_coluna",
        metrics=_aggregate_metrics_from_nodes(children),
        value=_sum_values(children),
        children=children,
    )


def _build_nivel1_from_assuntos(assuntos: dict) -> list[TreeNode]:
    """Constrói ASSUNTO_LINHA → PERGUNTA_LINHA → CATEGORIA_LINHA."""
    nivel1_children = []

    for assunto_linha, perguntas in assuntos.items():
        nivel2_children = []

        for pergunta_linha, leaves in perguntas.items():
            nivel3_children = []

            for row in leaves:
                leaf_node = TreeNode(
                    name=row.categoria_linha,
                    nivel="categoria_linha",
                    leaf=True,
                    metrics=LeafMetrics(
                        lift=float(row.lift) if row.lift else 0,
                        score_nexas=float(row.score_relevancia) if row.score_relevancia else 0,
                        relevancia=float(row.percentil_relevancia) if row.percentil_relevancia else 0,
                        direcao=row.direcao or "",
                        categoria_direcao=row.categoria_direcao or "",
                        rank_global=row.rank_global,
                        base_comum=row.base_cat_comum,
                        per_relativo=float(row.per_relativo) if row.per_relativo is not None else None,
                    ),
                    value=abs(float(row.score_relevancia)) if row.score_relevancia else 0,
                )
                nivel3_children.append(leaf_node)

            nivel3_children.sort(
                key=lambda n: n.metrics.score_nexas if n.metrics else 0,
                reverse=True,
            )

            nivel3_node = TreeNode(
                name=pergunta_linha,
                nivel="pergunta_linha",
                metrics=_aggregate_metrics(nivel3_children),
                value=_sum_values(nivel3_children),
                children=nivel3_children,
            )
            nivel2_children.append(nivel3_node)

        nivel2_children.sort(
            key=lambda n: n.metrics.avg_score if isinstance(n.metrics, NodeMetrics) else 0,
            reverse=True,
        )

        nivel2_node = TreeNode(
            name=assunto_linha,
            nivel="assunto_linha",
            metrics=_aggregate_metrics_from_nodes(nivel2_children),
            value=_sum_values(nivel2_children),
            children=nivel2_children,
        )
        nivel1_children.append(nivel2_node)

    nivel1_children.sort(
        key=lambda n: n.metrics.avg_score if isinstance(n.metrics, NodeMetrics) else 0,
        reverse=True,
    )

    return nivel1_children


def build_ramificacao(
    db: Session,
    onda_codigo: str,
    assunto_coluna: str,
    pergunta_coluna: str,
    categoria_coluna: str,
    direcao: str | None = None,
) -> TreeNode:
    onda = db.query(Onda).filter_by(codigo=onda_codigo).first()
    if not onda:
        raise ValueError(f"Onda '{onda_codigo}' não encontrada.")

    query = db.query(LiftResultado).filter(
        LiftResultado.onda_id == onda.id,
        LiftResultado.assunto_coluna == assunto_coluna,
        LiftResultado.pergunta_coluna == pergunta_coluna,
        LiftResultado.categoria_coluna == categoria_coluna,
    )

    if direcao:
        query = query.filter(LiftResultado.direcao == direcao)

    rows = query.all()

    if not rows:
        raise ValueError(f"Nenhum resultado para categoria_coluna='{categoria_coluna}'")

    return _build_from_categoria(rows, categoria_coluna)


# ── Agregação ──

def _calculate_composition(leaf_nodes: list[TreeNode]) -> dict | None:
    drivers, anti_drivers = [], []
    for node in leaf_nodes:
        if isinstance(node.metrics, LeafMetrics):
            if node.metrics.direcao == 'DRIVER':
                drivers.append(node.metrics.score_nexas)
            elif node.metrics.direcao == 'ANTI-DRIVER':
                anti_drivers.append(node.metrics.score_nexas)
    total = len(drivers) + len(anti_drivers)
    if total == 0:
        return None
    result = {}
    if drivers:
        result['drivers'] = {'count': len(drivers), 'percentage': round(len(drivers)/total*100,1), 'avg': round(sum(drivers)/len(drivers),1), 'max': round(max(drivers),1)}
    if anti_drivers:
        result['anti_drivers'] = {'count': len(anti_drivers), 'percentage': round(len(anti_drivers)/total*100,1), 'avg': round(sum(anti_drivers)/len(anti_drivers),1), 'min': round(min(anti_drivers),1)}
    return result if result else None


def _aggregate_metrics(leaf_nodes: list[TreeNode]) -> NodeMetrics:
    scores, relevancias = [], []
    for node in leaf_nodes:
        if isinstance(node.metrics, LeafMetrics):
            scores.append(node.metrics.score_nexas)
            relevancias.append(node.metrics.relevancia)
    avg_score = sum(scores)/len(scores) if scores else 0
    min_score = min(scores) if scores else 0
    max_score = max(scores) if scores else 0
    sorted_scores = sorted(scores) if scores else [0]
    n = len(sorted_scores)
    median_score = sorted_scores[n//2] if n%2 else (sorted_scores[n//2-1]+sorted_scores[n//2])/2
    std_dev = (sum((x-avg_score)**2 for x in scores)/len(scores))**0.5 if len(scores) > 1 else 0
    return NodeMetrics(
        avg_score=avg_score, min_score=min_score, max_score=max_score,
        median_score=median_score, std_dev=std_dev,
        avg_relevancia=sum(relevancias)/len(relevancias) if relevancias else 0,
        count=len(scores), composition=_calculate_composition(leaf_nodes),
    )


def _aggregate_metrics_from_nodes(child_nodes: list[TreeNode]) -> NodeMetrics:
    scores, relevancias, total_count = [], [], 0
    all_min, all_max, all_leaves = [], [], []

    def collect_leaves(node: TreeNode):
        if node.leaf:
            all_leaves.append(node)
        elif node.children:
            for c in node.children:
                collect_leaves(c)

    for node in child_nodes:
        collect_leaves(node)
        if isinstance(node.metrics, NodeMetrics):
            scores.append(node.metrics.avg_score)
            relevancias.append(node.metrics.avg_relevancia)
            total_count += node.metrics.count
            if node.metrics.min_score is not None: all_min.append(node.metrics.min_score)
            if node.metrics.max_score is not None: all_max.append(node.metrics.max_score)
        elif isinstance(node.metrics, LeafMetrics):
            scores.append(node.metrics.score_nexas)
            relevancias.append(node.metrics.relevancia)
            total_count += 1
            all_min.append(node.metrics.score_nexas)
            all_max.append(node.metrics.score_nexas)

    avg_score = sum(scores)/len(scores) if scores else 0
    sorted_scores = sorted(scores) if scores else [0]
    n = len(sorted_scores)
    median_score = sorted_scores[n//2] if n%2 else (sorted_scores[n//2-1]+sorted_scores[n//2])/2
    std_dev = (sum((x-avg_score)**2 for x in scores)/len(scores))**0.5 if len(scores) > 1 else 0

    return NodeMetrics(
        avg_score=avg_score,
        min_score=min(all_min) if all_min else 0,
        max_score=max(all_max) if all_max else 0,
        median_score=median_score, std_dev=std_dev,
        avg_relevancia=sum(relevancias)/len(relevancias) if relevancias else 0,
        count=total_count,
        composition=_calculate_composition(all_leaves) if all_leaves else None,
    )


def _sum_values(nodes: list[TreeNode]) -> float:
    return sum(n.value for n in nodes if n.value)
