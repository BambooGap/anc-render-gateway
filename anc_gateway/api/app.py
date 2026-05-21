from __future__ import annotations

from fastapi import FastAPI

from anc_gateway.api.routes import router

app = FastAPI(
    title="ANC Render Gateway",
    version="0.2.0",
    description="Minimal FastAPI service wrapper for the ANC parser kernel.",
)
app.include_router(router)
