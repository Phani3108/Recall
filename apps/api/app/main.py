from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import engine
from app.api.router import api_router
from app.middleware import GovernanceMiddleware, TokenBudgetMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # Startup
    yield
    # Shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Recall API",
        description="AI-Native Work OS — unified context, intelligent workflows",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env == "development" else None,
        redoc_url="/redoc" if settings.app_env == "development" else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(GovernanceMiddleware)
    app.add_middleware(TokenBudgetMiddleware)

    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
