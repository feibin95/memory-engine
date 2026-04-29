from fastapi import FastAPI
from pydantic import BaseModel, Field
from engine import engine

app = FastAPI(title="Memory Engine", version="0.1.0")


class WriteRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)


class RecallRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=20)


class MemoryResult(BaseModel):
    content: str
    score: float


class RecallResponse(BaseModel):
    user_id: str
    query: str
    results: list[MemoryResult]


@app.post("/write")
def write(req: WriteRequest):
    return engine.write(req.user_id, req.content)


@app.post("/recall", response_model=RecallResponse)
def recall(req: RecallRequest):
    return engine.recall(req.user_id, req.query, req.top_k)


@app.get("/health")
def health():
    return {"status": "ok"}
