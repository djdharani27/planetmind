# Tasks

## Completed

### Phase 1 — Project Initialization
- [x] Folder structure created
- [x] FastAPI backend with health endpoint
- [x] Configuration + env vars
- [x] Structured logging
- [x] SQLite database + documents table
- [x] React + Vite + Tailwind frontend
- [x] Vite proxy to backend
- [x] Architecture docs

### Phase 2-6 — Ingestion Pipeline
- [x] Document Upload API + drag & drop UI
- [x] Smart OCR Detection (PDF searchable vs scanned)
- [x] PaddleOCR Pipeline with confidence scores
- [x] Docling Parsing (headings, tables, lists)
- [x] Intelligent Chunking (LlamaIndex, prev/next IDs)
- [x] Extended formats: XLSX, CSV, EML, MSG, TXT, TIFF

### Phase 7-9 — Knowledge Layer
- [x] BGE-M3 Embeddings → Qdrant
- [x] Entity Extraction (LLM + regex, 10 types)
- [x] Neo4j Knowledge Graph (5 relationships including LOCATED_AT)
- [x] Equipment tags auto-populated from chunk text

### Phase 10-11 — Search & Chat
- [x] Hybrid Search (BM25 + Qdrant vector + Neo4j graph + BGE-Reranker)
- [x] AI Chat with citations, confidence, related entities
- [x] Chat Streaming endpoint (SSE)
- [x] Search filters (equipment, date, type, technician, failure)

### Phase 12-16 — UI Pages
- [x] Dashboard (8 metrics, live job progress)
- [x] Upload Page (drag & drop, multi-file queue)
- [x] Search Page (with functional filters)
- [x] Chat Page (citations, confidence, entities)
- [x] Document Viewer (OCR text, parsed structure, entities, chunks)
- [x] Knowledge Graph UI (vis-network interactive canvas)
- [x] Processing Status (background jobs, live progress bar)

### Phase 17-18 — Advanced Agents & Testing
- [x] Maintenance Intelligence & RCA Agent
- [x] Quality & Regulatory Compliance Intelligence
- [x] Lessons Learned & Failure Intelligence Engine
- [x] Background job system with live progress polling
- [x] 42 unit/API/integration tests (all passing)
- [x] Mobile-responsive nav with hamburger menu
- [x] LLM prompts externalized to files
- [x] README with full documentation

### Phase 19 — Production Readiness
- [x] README with quick start and full API docs
- [x] Complete track.md with all endpoints/frontend pages
- [ ] Docker Compose (explicitly deferred per requirements)

## Pending
- Docker Compose configuration (intentionally deferred)
- CI/CD pipeline
- Production GPU setup for ML dependencies
