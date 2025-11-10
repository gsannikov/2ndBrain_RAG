# Local RAG + MCP + OCR (MacBook Air M‑series)

Local-first retrieval over a mirrored folder of PDFs and documents. Includes a Model Context Protocol (MCP) server that Claude Desktop/Claude Code can call. Watches the folder, indexes changes, performs OCR for scanned PDFs/images, and returns passages with citations.

## Features
- File watcher for create/modify/delete.
- Text extraction for PDF/Docx/PPTX/XLSX/Markdown/TXT.
- OCR: Surya by default (CPU), PaddleOCR optional, DeepSeek-OCR optional.
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (CPU/MPS).
- Vector store: Chroma persistent.
- MCP tools: `rag.search`, `rag.get`, `rag.reindex`, `rag.stats`, `rag.invalidate`.

## Requirements
- macOS on Apple Silicon. Python 3.11+.
- Homebrew: `brew install poppler libmagic`.
- Claude Desktop or Claude Code (installed already).

## Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env -> set ROOT_DIR to your mirrored folder
```

## Run
```bash
source .venv/bin/activate
python mcp_server.py
```

## Connect to Claude
Create or edit your Claude MCP config and add this server:
```json
{
  "mcpServers": {
    "local-rag": {
      "command": "python",
      "args": ["-u", "mcp_server.py"],
      "env": { "PYTHONUNBUFFERED": "1" }
    }
  }
}
```
Place it at the location Claude Desktop/Claude Code expects, or merge it into an existing file. Then restart Claude.

## Usage examples (inside Claude)
- `rag.stats` → index stats.
- `rag.search { "query": "invoice policy", "k": 6 }` → top passages with paths and offsets.
- `rag.get { "path": "/path/doc.pdf", "start": 1234, "end": 2100 }` → source window.
- After edits: `rag.reindex` or `rag.reindex { "paths": ["/path/file.pdf"] }`.

## .env
See `.env.example`. Default OCR engine is Surya for laptops. DeepSeek-OCR is optional.

## Notes
- Default DPI 200 for OCR to reduce heat. Re‑OCR specific pages at 300 only if needed.
- For corpora > ~5–10 GB consider Qdrant and hybrid BM25 + vectors.
