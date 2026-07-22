"""
routers/tree.py — Endpoints do dendrograma.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.tree import TreeResponse, TreeNode, MetricasResumo
from backend.services.tree_builder import build_tree, build_ramificacao
from backend.services.aggregator import get_metricas_resumo

router = APIRouter(prefix="/api", tags=["visualizações"])


@router.get("/tree", response_model=TreeResponse)
def get_tree(
    onda: str = Query(...),
    assunto: str = Query(...),
    pergunta: str = Query(...),
    categoria_coluna: str | None = Query(None, description="Filtro opcional — muda o root da árvore para 3 níveis"),
    direcao: str | None = Query(None),
    agregacao: str = Query("weighted_mean"),
    db: Session = Depends(get_db),
):
    try:
        return build_tree(db, onda, assunto, pergunta, direcao, agregacao, categoria_coluna)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/ramificacao", response_model=TreeNode)
def get_ramificacao(
    onda: str = Query(...),
    assunto: str = Query(...),
    pergunta: str = Query(...),
    categoria: str = Query(...),
    direcao: str | None = Query(None),
    db: Session = Depends(get_db),
):
    try:
        return build_ramificacao(db, onda, assunto, pergunta, categoria, direcao)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/metricas", response_model=MetricasResumo)
def get_metricas(
    onda: str = Query(...),
    assunto: str = Query(...),
    pergunta: str = Query(...),
    direcao: str | None = Query(None),
    db: Session = Depends(get_db),
):
    try:
        return get_metricas_resumo(db, onda, assunto, pergunta, direcao)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
