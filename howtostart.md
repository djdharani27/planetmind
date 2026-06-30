# How to Start PlanetMind AI from Scratch

## Prerequisites

- **Python 3.12+** with pip
- **Node.js 22+** with npm
- **Docker** (for Qdrant + Neo4j)
- **OpenRouter API key** (or any OpenAI-compatible key) — set in `.env`

---

## Step 1 — Clone & Navigate

```bash
git clone https://github.com/djdharani27/planetmind.git
cd planetmind/app
```

---

## Step 2 — Set Up Environment

Copy the example env file and fill in your LLM key:

```bash
cp .env.example .env
```

Edit `.env` and set your values. The only required key is:

```
LLM_API_KEY=sk-or-v1-your-openrouter-key
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free
```

Everything else (Qdrant, Neo4j, JWT) has sensible defaults that work out of the box.

---

## Step 3 — Start External Services (Qdrant + Neo4j)

```bash
docker compose -f docker/docker-compose.yml up -d qdrant neo4j
```

Wait for both to be healthy (~15 seconds):

```bash
docker ps
# Both should show "(healthy)"
```

Verify Qdrant:

```bash
curl http://localhost:6333/health
# → {"title":"qdrant - vector search engine","version":"1.13.0"}
```

Verify Neo4j:

```bash
curl http://localhost:7474
# → (JSON response from Neo4j HTTP API)
```

---

## Step 4 — Install Dependencies

```bash
# Backend
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

This installs FastAPI, Uvicorn, PyMuPDF, PaddleOCR, Docling, LlamaIndex, FlagEmbedding (BGE-M3 + BGE-Reranker), Qdrant client, Neo4j driver, JWT libraries, and React with Tailwind.

---

## Step 5 — Start the Application

Open two terminals.

**Terminal 1 — Backend:**
```bash
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend && npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Step 6 — Login

The database seeds a default admin user on first start.

```
Username: admin
Password: admin123
```

---

## Step 7 — Upload & Process Documents

1. Go to **Upload** page
2. Drag & drop PDFs, DOCX, TXT, CSV, XLSX, EML, JPEG, PNG, TIFF
3. Click **Upload All**
4. Each document auto-processes through the pipeline:
   - OCR / text extraction
   - Docling structured parsing (headings, tables, lists)
   - LlamaIndex chunking
   - BGE-M3 embeddings → Qdrant
   - Entity extraction → Neo4j knowledge graph
5. Check **Dashboard** for live pipeline progress

---

## Running with Docker Compose (Full Stack)

To run everything in containers:

```bash
docker compose -f docker/docker-compose.yml up -d
```

This starts backend, frontend, Qdrant, and Neo4j. Open http://localhost:80.

Note: Docker Compose backend needs `--reload` removed and runs on port 80 via nginx.

---

## Quick Start Summary

```bash
# 1. Clone
git clone https://github.com/djdharani27/planetmind.git && cd planetmind/app

# 2. Configure
cp .env.example .env
# → edit .env with your LLM_API_KEY

# 3. External services
docker compose -f docker/docker-compose.yml up -d qdrant neo4j

# 4. Install
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..

# 5. Run backend (terminal 1)
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000

# 6. Run frontend (terminal 2)
cd frontend && npm run dev

# 7. Open http://localhost:5173
#    Login: admin / admin123
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Qdrant `query_points` error | Upgrade `qdrant-client` — `pip install --upgrade qdrant-client` |
| Docling `metadata` error | Docling API changed between versions; falls back to simple parse automatically |
| BGE reranker `prepare_for_model` error | Update `FlagEmbedding` — `pip install --upgrade FlagEmbedding` |
| Port 8000 already in use | `netstat -ano \| findstr 8000` then `taskkill /PID <pid>` (Windows) |
| Frontend 401 errors | Login first; token stored in localStorage |
| Pipeline jobs lost on restart | Use `--reload` carefully — file changes kill background threads. For development, restart manually after code changes |
| Neo4j/graph zero results | Verify `http://localhost:7474` responds. Run `docker ps` to confirm container is healthy |
| Qdrant/vectors zero results | Check `curl http://localhost:6333/health`. Pipeline creates collection automatically on first embedding run |
