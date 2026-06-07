from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from pipeline.orchestrator import Orchestrator
from protocol.message import ReviewResult

app = FastAPI(title="Multi-Agent Code Review", version="0.1.0")
orchestrator = Orchestrator()


class ReviewRequest(BaseModel):
    filename: str
    code: str
    diff: str | None = None


@app.post("/review", response_model=ReviewResult)
async def review(req: ReviewRequest) -> ReviewResult:
    if not req.code.strip():
        raise HTTPException(status_code=400, detail="code must not be empty")
    return await orchestrator.review(req.code, req.filename, req.diff)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
