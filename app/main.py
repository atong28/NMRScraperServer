from pathlib import Path
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .processing import condense_text, parse_markdown_tables

# --- Resolve project paths relative to this file, not CWD ---
BASE_DIR = Path(__file__).resolve().parent.parent  # project root
STATIC_DIR = BASE_DIR / "static"
INDEX_HTML = STATIC_DIR / "index.html"

app = FastAPI(title="Simple Processing Server", version="0.1.0")

# Serve static files with an absolute path
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def index():
    # Serve the SPA
    return FileResponse(str(INDEX_HTML))

# --- API models ---
class TextIn(BaseModel):
    text: str

class MarkdownIn(BaseModel):
    markdown: str

class CondensedOut(BaseModel):
    condensed: str

# --- API routes ---
@app.post("/api/condense", response_model=CondensedOut)
async def api_condense(payload: TextIn):
    return {"condensed": condense_text(payload.text)}

@app.post("/api/parse_markdown_tables")
async def api_parse_md_tables(payload: MarkdownIn) -> Dict[str, List[Dict[str, Any]]]:
    tables = parse_markdown_tables(payload.markdown)
    return {"tables": tables}
