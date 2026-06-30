# Tasks

## Pending

### Phase 2 — Document Upload
- [ ] Upload API endpoint (POST /api/documents/upload)
- [ ] File validation (type, size)
- [ ] Save to storage/uploads/
- [ ] Metadata record in SQLite
- [ ] Drag & drop UI component
- [ ] Upload progress indicator
- [ ] Basic document list API (GET /api/documents)

### Phase 3 — Smart OCR Detection
- [ ] PDF type detection (searchable vs scanned)
- [ ] Image format detection
- [ ] Native text extraction for searchable PDFs
- [ ] OCR routing decision logic

### Phase 4 — OCR Pipeline
- [ ] PaddleOCR integration
- [ ] OCR extraction with confidence scores
- [ ] Page-by-page processing
- [ ] Save OCR output to storage/processed/

### Phase 5 — Document Parsing
- [ ] Docling integration
- [ ] Heading extraction
- [ ] Table extraction
- [ ] List extraction
- [ ] Document hierarchy

### Phase 6 — Chunking
- [ ] LlamaIndex Node Parser integration
- [ ] Chunk by headings, sections, token limits
- [ ] Chunk metadata (ID, doc ID, page, prev/next)
- [ ] Save chunks to database

### Phase 7 — Embedding Pipeline
- [ ] BGE-M3 integration
- [ ] Generate embeddings for all chunks
- [ ] Store in Qdrant

### Phase 8 — Entity Extraction
- [ ] LLM integration
- [ ] Prompt engineering for industrial entities
- [ ] Entity schema + JSON validation

### Phase 9 — Knowledge Graph
- [ ] Neo4j connection
- [ ] Node creation (equipment, failure, technician, etc.)
- [ ] Relationship creation
- [ ] Graph ingestion pipeline

### Phase 10 — Hybrid Search
- [ ] BM25 keyword search
- [ ] Qdrant vector search
- [ ] Neo4j graph search
- [ ] Result merge + reranker

### Phase 11 — AI Chat
- [ ] Context builder
- [ ] LLM chat endpoint
- [ ] Citations + confidence scores
- [ ] Streaming response

### Phase 12 — Dashboard
- [ ] Metrics API
- [ ] Dashboard UI (documents, chunks, entities, graph)

### Phase 13 — Document Viewer
- [ ] PDF viewer
- [ ] OCR text display
- [ ] Metadata panel
- [ ] Entity panel

### Phase 14 — Knowledge Graph UI
- [ ] Interactive graph visualization
- [ ] Node details panel
- [ ] Linked documents

### Phase 15 — Search UI
- [ ] Search bar with filters
- [ ] Results list
- [ ] Similarity scores

### Phase 16 — Processing Status
- [ ] Pipeline progress tracking
- [ ] Background job system
- [ ] Progress API + UI

### Phase 17 — Testing
- [ ] Unit tests
- [ ] API tests
- [ ] Integration tests

### Phase 18 — Optimization
- [ ] Performance tuning
- [ ] Caching
- [ ] Error handling improvements
- [ ] Documentation

### Phase 19 — Production Readiness
- [ ] Docker Compose
- [ ] Deployment scripts
- [ ] README
- [ ] Environment setup docs

---

## Completed

### Phase 1 — Project Initialization
- [x] Folder structure created
- [x] FastAPI backend with health endpoint
- [x] Configuration + env vars
- [x] Structured logging
- [x] SQLite database + documents table
- [x] React + Vite + Tailwind frontend
- [x] Vite proxy to backend
- [x] Architecture docs (track.md, tasks.md, architecture.md)
