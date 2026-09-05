from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .webapi import analyze_full

app = FastAPI(title="CodeGate API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze")
async def analyze(request: Request):
    data = await request.json()
    source = data.get("source", "")
    filename = data.get("filename", "input.py")
    fix = bool(data.get("fix", False))
    ensemble = bool(data.get("ensemble", False))
    if not source.strip():
        raise HTTPException(status_code=400, detail="source is required")
    try:
        result = analyze_full(source, filename=filename, fix=fix, ensemble=ensemble)
        return JSONResponse(content=result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/health")
async def health():
    return {"ok": True, "service": "CodeGate", "version": "0.1.0"}
