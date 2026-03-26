"""
NyayaBot API Server - Fixed static file serving
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, List, Dict
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel
import uvicorn

# ===== CRITICAL: Load .env FIRST before anything else =====
BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / ".env"

from dotenv import load_dotenv
load_dotenv(ENV_FILE, override=True)

# Verify key loaded
_groq_key = os.getenv("GROQ_API_KEY", "")
_anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

if _groq_key and _groq_key != "your_groq_api_key_here":
    print(f"✅ Groq API key loaded: {_groq_key[:15]}...")
elif _anthropic_key and _anthropic_key != "your_anthropic_api_key_here":
    print(f"✅ Anthropic API key loaded: {_anthropic_key[:15]}...")
else:
    print("❌ WARNING: No AI API key found in .env!")
    print(f"   Add GROQ_API_KEY=gsk_... to: {ENV_FILE}")
    print("   Get free key at: console.groq.com")

sys.path.insert(0, str(BASE_DIR))
from rag.engine import NyayaBotRAGEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NyayaBot API", version="1.0.0", docs_url="/api/docs", redoc_url="/api/redoc")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

frontend_path = BASE_DIR / "frontend"
engine: Optional[NyayaBotRAGEngine] = None

@app.on_event("startup")
async def startup():
    global engine
    logger.info("Initializing NyayaBot RAG Engine...")
    os.chdir(BASE_DIR)
    engine = NyayaBotRAGEngine(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        vector_store_path=str(BASE_DIR / "data" / "faiss_index"),
        policies_dir=str(BASE_DIR / "data" / "policies")
    )
    logger.info("NyayaBot ready!")

class ChatRequest(BaseModel):
    message: str
    language: str = "en"
    session_id: Optional[str] = None
    history: Optional[List[Dict]] = None

class ChatResponseModel(BaseModel):
    answer: str
    language: str
    sources: List[str]
    scheme_names: List[str]
    retrieval_time_ms: float
    llm_time_ms: float
    total_time_ms: float
    confidence: float
    session_id: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    engine_loaded: bool
    chunks_in_index: int
    version: str

# ===== API ROUTES =====
@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok", engine_loaded=engine is not None,
        chunks_in_index=len(engine.vector_store.chunks) if engine else 0,
        version="1.0.0"
    )

@app.post("/api/chat", response_model=ChatResponseModel)
async def chat(request: ChatRequest):
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    try:
        result = engine.chat(
            user_message=request.message,
            language=request.language,
            conversation_history=request.history
        )
        return ChatResponseModel(
            answer=result.answer, language=result.language, sources=result.sources,
            scheme_names=result.scheme_names, retrieval_time_ms=result.retrieval_time_ms,
            llm_time_ms=result.llm_time_ms, total_time_ms=result.total_time_ms,
            confidence=result.confidence, session_id=request.session_id
        )
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-policy")
async def upload_policy(file: UploadFile = File(...), scheme_name: Optional[str] = None):
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    content = await file.read()
    suffix = Path(file.filename).suffix.lower()
    scheme = scheme_name or Path(file.filename).stem.replace('_', ' ').title()
    if suffix == '.pdf':
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        chunks = engine.processor.process_pdf(tmp_path, scheme)
        if chunks:
            engine.vector_store.add_chunks(chunks, engine.embedder)
            engine.vector_store.save()
        Path(tmp_path).unlink(missing_ok=True)
        chunks_added = len(chunks)
    else:
        text = content.decode('utf-8', errors='ignore')
        chunks_added = engine.add_document(text, scheme, file.filename)
    return {"success": True, "chunks_added": chunks_added, "scheme_name": scheme}

@app.get("/api/schemes")
async def list_schemes():
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    schemes = {}
    for chunk in engine.vector_store.chunks:
        s = chunk.scheme_name
        schemes[s] = schemes.get(s, {"name": s, "chunk_count": 0, "source": chunk.source_file})
        schemes[s]["chunk_count"] += 1
    return {"schemes": list(schemes.values()), "total": len(schemes)}

@app.get("/api/search")
async def semantic_search(q: str, top_k: int = 5):
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    results = engine.retrieve(q, top_k=top_k)
    return {"query": q, "results": [
        {"scheme": r.chunk.scheme_name, "section": r.chunk.section,
         "content": r.chunk.content[:300] + "...", "score": round(r.score, 3)}
        for r in results
    ]}

@app.get("/api/stats")
async def get_stats():
    if not engine:
        return {"error": "Engine not initialized"}
    chunks = engine.vector_store.chunks
    scheme_counts = {}
    for c in chunks:
        scheme_counts[c.scheme_name] = scheme_counts.get(c.scheme_name, 0) + 1
    return {"total_chunks": len(chunks), "total_schemes": len(scheme_counts), "scheme_distribution": scheme_counts}

# ===== FRONTEND FILE ROUTES (after /api routes) =====
@app.get("/style.css")
async def serve_css():
    return FileResponse(str(frontend_path / "style.css"), media_type="text/css")

@app.get("/app.js")
async def serve_js():
    return FileResponse(str(frontend_path / "app.js"), media_type="application/javascript")

@app.get("/dashboard.html")
async def serve_dashboard():
    return FileResponse(str(frontend_path / "dashboard.html"), media_type="text/html")

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

@app.get("/")
async def root():
    index = frontend_path / "index.html"
    if index.exists():
        return FileResponse(str(index), media_type="text/html")
    return JSONResponse({"message": "NyayaBot API", "docs": "/api/docs"})

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False, log_level="info")
