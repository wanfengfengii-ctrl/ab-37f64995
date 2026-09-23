"""FastAPI application: beam pulse reconciliation workbench API."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .models import AdjudicateRequest, AdjudicateResponse
from .solver import solve

app = FastAPI(title="Beam Pulse Reconciliation API", version="1.0.0")

# The UI is served by its own container; CORS is open for local deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """Liveness/readiness probe."""
    return {"status": "ok"}


@app.post("/api/adjudicate", response_model=AdjudicateResponse)
def adjudicate(req: AdjudicateRequest) -> dict:
    """Run the reconciliation verdict over two edited/imported event streams."""
    result = solve(
        times_a=[e.time for e in req.stream_a],
        codes_a=[e.code for e in req.stream_a],
        times_b=[e.time for e in req.stream_b],
        codes_b=[e.code for e in req.stream_b],
        min_offset=req.min_offset,
        max_offset=req.max_offset,
        jump=req.jump,
        min_hits=req.min_hits,
    )
    result["min_hits"] = req.min_hits
    return result
