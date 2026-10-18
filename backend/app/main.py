"""LedgerGuard FastAPI application factory."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.models import ErrorResponse
from backend.app.api.routes import build_router
from backend.app.data import QuickBooksDatasetLoader, QuickBooksNormalizer
from backend.app.data.store import NormalizedAccountingStore
from backend.app.db import AuditRepository
from backend.app.policy import PolicyEngine
from backend.app.providers import (
    GeminiBaselineProvider, OpenJevProvider, ProviderRegistry, RulesProvider,
    SystemOneProvider,
)
from backend.app.services.application import ApplicationError, LedgerGuardApplication
from backend.app.services.context_builder import ContextBuilder


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def build_default_service() -> LedgerGuardApplication:
    dataset = Path(os.getenv("LEDGERGUARD_DATASET", PROJECT_ROOT / "data/raw/hackathon-100"))
    db_path = Path(os.getenv("LEDGERGUARD_DB_PATH", PROJECT_ROOT / "data/ledgerguard.sqlite3"))
    store = NormalizedAccountingStore(
        QuickBooksDatasetLoader(dataset), QuickBooksNormalizer()
    )
    providers = ProviderRegistry()
    providers.register("rules", RulesProvider())
    providers.register("gemini", GeminiBaselineProvider())
    providers.register("system_one", SystemOneProvider())
    providers.register("openjev", OpenJevProvider())
    return LedgerGuardApplication(
        AuditRepository(db_path), ContextBuilder(store), providers, PolicyEngine(),
        scenarios_path=PROJECT_ROOT / "data/scenarios/scenarios.jsonl",
        benchmark_dir=PROJECT_ROOT / "evaluation/results",
        checkpoint_path=db_path.with_name(f"{db_path.stem}.checkpoints.sqlite3"),
    )


def create_app(
    service: LedgerGuardApplication | None = None,
    *,
    cors_origins: tuple[str, ...] | None = None,
) -> FastAPI:
    service = service or build_default_service()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await service.aclose()

    app = FastAPI(title="LedgerGuard API", version="1.0.0", lifespan=lifespan)
    app.state.ledgerguard = service
    origins = cors_origins or tuple(
        origin.strip()
        for origin in os.getenv(
            "LEDGERGUARD_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
        ).split(",")
        if origin.strip()
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Last-Event-ID"],
    )
    app.include_router(build_router(service))

    @app.exception_handler(ApplicationError)
    async def application_error(_: Request, exc: ApplicationError) -> JSONResponse:
        body = ErrorResponse(
            code=exc.code, message=exc.message, retryable=exc.retryable
        )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        body = ErrorResponse(code="VALIDATION_ERROR", message="request validation failed")
        return JSONResponse(status_code=422, content=body.model_dump(mode="json"))

    return app


app = create_app()
