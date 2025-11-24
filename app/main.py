from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.db.elasticsearch import es_client
from app.api.routes import variant, gene, region, stats

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await es_client.connect()
    yield
    # Shutdown
    await es_client.close()

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        lifespan=lifespan
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=False, # We do not need cookies/auth for this variant API
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include Routers
    app.include_router(variant.router, prefix="/variant", tags=["variant"])
    app.include_router(gene.router, prefix="/gene", tags=["gene"])
    app.include_router(region.router, prefix="/region", tags=["region"])
    app.include_router(stats.router, tags=["stats"])

    # Static Files (Production)
    # Note: In a real production env, Nginx should handle this.
    # We keep it here for the Docker convenience.
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "api.py")
    # The above path is tricky because we are in app/main.py. 
    # Let's assume the static folder is relative to the root, where api.py is.
    root_dir = os.getcwd()
    static_dir = os.path.join(root_dir, "static")

    if os.path.exists(static_dir):
        assets_dir = os.path.join(static_dir, "assets")
        if os.path.exists(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            file_path = os.path.join(static_dir, full_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(os.path.join(static_dir, "index.html"))

    return app

app = create_app()
