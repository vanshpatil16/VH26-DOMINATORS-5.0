from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from .server import _ananalyze, _analyze_batch, _Handler  # reuse the existing logic

app = FastAPI(title="CodeGate API", version="0.1.0")


@app.post("/ananalyze")
async def analyze(req: Request):
    data = await req.json()
    try:
        result = _analyze(data)
        return JSONResponse(content=result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/analyze-batch")
async def analyze_batch(req: Request):
    data = await req.json()
    try:
        result = _analyze_batch(data)
        return JSONResponse(content=result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health():
    # reuse the health logic from the original server
    cache = _Handler.cache
    return {
        "ok": True,
        "cached": len(cache._data),
        "cache_hits": cache.hits,
        "cache_misses": cache.misses,
    }
