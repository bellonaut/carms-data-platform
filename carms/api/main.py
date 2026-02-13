from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from carms.api.deps import rate_limit, require_api_key
from carms.api.routes import analytics, disciplines, geomap, pipeline, programs, semantic


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan to initialize resources on startup."""
    from carms.core.database import init_db

    init_db()
    yield
    # no shutdown actions required


def create_app() -> FastAPI:
    app = FastAPI(
        title="CaRMS Platform API",
        version="0.1.0",
        lifespan=lifespan,
        dependencies=[Depends(rate_limit), Depends(require_api_key)],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(programs.router)
    app.include_router(disciplines.router)
    app.include_router(pipeline.router)
    app.include_router(geomap.router)
    app.include_router(semantic.router)
    app.include_router(analytics.router)

    class HealthResponse(BaseModel):
        status: str

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    return app


app = create_app()
