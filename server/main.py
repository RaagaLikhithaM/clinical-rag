"""
server/main.py

FastAPI application exposing two endpoints:

POST /ingest  — accepts one or more PDF files, runs the ingestion
                pipeline, and returns a summary for each file.

POST /query   — accepts a user question, runs the full RAG pipeline,
                and returns a cited answer.

We keep the endpoints thin. All logic lives in the agent package.
"""

import os
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import ingest_pdf, run_query

app = FastAPI(
    title="Clinical Protocol RAG API",
    description="Retrieval-augmented generation over clinical guidelines.",
    version="1.0.0",
)

# Allow the Streamlit frontend running on localhost to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══ Request and response models ════════════════════════════════════════════════

class QueryRequest(BaseModel):
    """Request body for the query endpoint."""
    question: str


class QueryResponse(BaseModel):
    """Response body for the query endpoint."""
    answer:    str
    sources:   list[str]
    intent:    str
    top_score: float


class IngestResponse(BaseModel):
    """Response body for one ingested file."""
    source:  str
    status:  str
    pages:   int = 0
    chunks:  int = 0


# ══ Endpoints ══════════════════════════════════════════════════════════════════

@app.post("/ingest", response_model=list[IngestResponse])
async def ingest(files: list[UploadFile] = File(...)):
    """Accept one or more PDF files and ingest them into the database.

    Each file is saved to a temporary location, processed by the
    ingestion pipeline, then the temporary file is deleted. This keeps
    the server stateless with respect to uploaded files.

    Returns a list of ingestion summaries, one per file.
    """
    results = []
    for upload in files:
        if not upload.filename.endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"{upload.filename} is not a PDF file."
            )

        # Save to a temp file so pdfplumber can open it by path
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".pdf"
        ) as tmp:
            shutil.copyfileobj(upload.file, tmp)
            tmp_path = tmp.name

        try:
            summary = ingest_pdf(tmp_path, source_name=upload.filename)
            # Use the original filename as the source identifier
            summary["source"] = upload.filename
            results.append(IngestResponse(**summary))
        finally:
            os.unlink(tmp_path)

    return results


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Accept a user question and return a cited answer.

    The pipeline handles intent detection, retrieval, and generation.
    If the knowledge base is empty or the question is out of scope,
    the answer field explains why rather than raising an error.

    Returns a structured response with the answer, sources, intent
    classification, and the top retrieval similarity score.
    """
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    result = run_query(request.question)
    return QueryResponse(**result)


@app.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "ok"}