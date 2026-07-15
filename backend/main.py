"""
main.py — Ponto de entrada da aplicação FastAPI.
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import settings
from backend.database import engine, Base
from backend.routers import filtros, tree, ingestao, tabela

logging.basicConfig(
    level=logging.INFO if settings.is_development else logging.WARNING,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NEXAS Analytics",
    description="Dashboard analítico de visualização de associações (Lift Condicional)",
    version="2.0.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers da API ──
app.include_router(filtros.router)
app.include_router(tree.router)
app.include_router(ingestao.router)
app.include_router(tabela.router)

# ── Caminhos do frontend ──
frontend_path = Path(__file__).parent.parent / "frontend"

# ── Rota explícita para subpastas do frontend ──
# O StaticFiles montado na raiz não serve subpastas de forma confiável
# quando há rotas de API conflitantes. Registramos explicitamente.
@app.get("/pages/{page_name}")
def serve_page(page_name: str):
    """Serve arquivos da pasta frontend/pages/."""
    page_file = frontend_path / "pages" / page_name
    if page_file.exists() and page_file.is_file():
        return FileResponse(str(page_file))
    return FileResponse(str(frontend_path / "index.html"))

@app.get("/js/{file_name}")
def serve_js(file_name: str):
    """Serve arquivos da pasta frontend/js/."""
    js_file = frontend_path / "js" / file_name
    if js_file.exists() and js_file.is_file():
        return FileResponse(str(js_file))
    return FileResponse(str(frontend_path / "index.html"))

# ── Arquivos estáticos (css, assets) ──
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
    logger.info(f"Frontend servido de: {frontend_path}")
else:
    logger.warning(f"Pasta frontend não encontrada: {frontend_path}")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    logger.info("NEXAS Analytics iniciado")
    logger.info(f"Ambiente: {settings.app_env}")
    logger.info(f"Docs disponível em: http://localhost:{settings.app_port}/docs")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}
