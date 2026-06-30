# PlanetMind AI

**Universal Document Ingestion & Knowledge Graph Agent** — AI pipeline that processes PDFs, P&IDs, scanned forms, spreadsheets, and email archives, extracting entities and building a unified knowledge graph.

## Quick Start

```bash
# Backend
cd planetmind/app
pip install -r backend/requirements.txt
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd planetmind/app/frontend
npm install
npm run dev
```

Open http://localhost:5173

## External Services

For full functionality, these must be running:

| Service | Port | Purpose |
|---|---|---|
| Qdrant | 6333 | Vector embeddings |
| Neo4j | 7687 | Knowledge graph |
| LLM (OpenAI-compatible) | - | Entity extraction & chat |

Without them, the platform falls back to regex-based extraction and keyword matching.

## Architecture

```
upload → OCR detection → PaddleOCR/native extraction → Docling parsing
     → chunking → BGE-M3 embeddings → Qdrant
     → entity extraction → Neo4j knowledge graph → Ready for search
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/documents/upload` | Upload document |
| `GET` | `/api/documents` | List documents |
| `GET` | `/api/documents/{id}` | Get document |
| `DELETE` | `/api/documents/{id}` | Delete document |
| `POST` | `/api/pipeline/process` | Run processing pipeline |
| `POST` | `/api/search` | Hybrid search (BM25 + vector + graph) |
| `POST` | `/api/chat` | AI chat with RAG |
| `GET` | `/api/dashboard` | Dashboard metrics |
| `POST` | `/api/maintenance/rca` | Root Cause Analysis |
| `POST` | `/api/maintenance/predict` | Predictive maintenance |
| `POST` | `/api/compliance/analyze` | Compliance gap analysis |
| `POST` | `/api/compliance/audit` | Audit evidence package |
| `POST` | `/api/lessons/analyze` | Lessons learned analysis |
| `POST` | `/api/lessons/warnings` | Proactive failure warnings |

## AI Agents

### Expert Knowledge Copilot
RAG-powered conversational AI for operational, maintenance, and engineering queries with source citations and confidence scores.

### Maintenance Intelligence & RCA Agent
Fuses work orders, failure records, OEM manuals, and inspection findings to generate predictive maintenance recommendations and Root Cause Analysis.

### Quality & Regulatory Compliance Intelligence
Maps regulations (Factory Act, OISD, PESO, ISO) against procedures — identifying gaps, generating audit evidence, and flagging deviations.

### Lessons Learned & Failure Intelligence Engine
Analyzes incident reports and near-misses to identify systemic patterns, cross-referencing with industry databases and pushing proactive warnings.

## Supported File Types

PDF, DOCX, XLSX, CSV, EML, MSG, TXT, JPG, PNG, TIFF — scanned manuals, SOPs, incident reports, inspection reports, OEM manuals, spreadsheets, email archives.

## Folder Structure

```
planetmind/
├── backend/
│   ├── api/routes/        # FastAPI routes
│   ├── ingestion/         # OCR, parsing, chunking
│   ├── embeddings/        # BGE-M3 → Qdrant
│   ├── search/            # Hybrid search
│   ├── graph/             # Neo4j knowledge graph
│   ├── llm/               # Chat, entities, agents
│   ├── database/          # SQLite
│   ├── models/            # Pydantic models
│   └── utils/
├── frontend/
│   └── src/pages/         # React pages
├── storage/               # Uploads, processed, cache
└── prompts/               # LLM prompt templates
```

## Testing

```bash
python -m pytest backend/tests/ -v
```

## License

Proprietary
