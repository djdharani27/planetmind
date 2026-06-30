# Tasks

## Phase 1 — Environment & Configuration

**Goal:** Make all external services (LLM, Qdrant, Neo4j) configurable and instantiable. Wire externalized prompts.

- [ ] Add env vars to `.env` and `config.py`: `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `QDRANT_HOST`, `QDRANT_PORT`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- [ ] Create `backend/llm/client.py` — `create_llm_client()` factory function returning an OpenAI-compatible client configured from env vars
- [ ] Update `GPTNeo4jClient` (or equivalent) instantiation in `graph_builder.py`, `graph_api.py`, `dashboard.py` to read from config instead of hardcoded `"neo4j"/"password"`
- [ ] Update `embedder.py`, `dashboard.py` Qdrant host/port to read from config instead of hardcoded `"localhost":6333`
- [ ] Update `chat_assistant.py`, `maintenance_rca.py`, `compliance_intel.py`, `lessons_engine.py` to load prompt text from `prompts/*.txt` files instead of hardcoded string constants
- [ ] Update all `model="gpt-4o-mini"` hardcoded strings to use `settings.llm_model`

**Verify:** All hardcoded credentials and model names removed. `.env` file has complete config.

---

## Phase 2 — LLM Client Wiring

**Goal:** Instantiate and pass the LLM client through all entry points so AI features use real LLM instead of fallbacks.

- [ ] Wire `create_llm_client()` into `chat_assistant.generate_answer()`, `maintenance_rca.analyze_maintenance()`, `compliance_intel.analyze_compliance()`, `lessons_engine.analyze_lessons()` — remove `llm_client=None` default, make it required or auto-create internally
- [ ] Wire `create_llm_client()` into `pipeline.process_document()` and call `entity_extractor.extract_entities()` (LLM path) instead of `_regex_extract()`
- [ ] Wire `create_llm_client()` into the API routes: `chat.py`, `maintenance.py`, `compliance.py`, `lessons.py` so they pass `llm_client` downstream
- [ ] Add graceful fallback: if LLM client creation fails, log warning and fall back to regex/hardcoded answers (existing behavior preserved as fallback)

**Verify:** Upload a document, run chat/RCA/compliance/lessons — LLM generates real responses. Disconnect LLM — graceful fallback still works.

---

## Phase 3 — Pipeline Integration

**Goal:** Main `process_document()` uses dedicated modules (Docling parser, LlamaIndex chunker, BGE-M3 embedder) instead of inline simplified fallbacks.

- [ ] Replace `_simple_parse()` with `ingestion/docling/parser.parse_document()` — structured heading/table/list extraction
- [ ] Replace `_simple_chunk()` with `ingestion/chunking/chunker.chunk_text()` — LlamaIndex SentenceSplitter with prev/next IDs
- [ ] Call `embeddings/embedder.generate_and_store_embeddings()` from `process_document()` instead of skipping (`skipped_no_service`)
- [ ] Keep fallback: if Docling/chunker/embedder raise (missing deps, service down), fall back to `_simple_parse`, `_simple_chunk`, skip embeddings — existing behavior preserved
- [ ] Remove `next_chunk_id` fix-up loop in `_simple_chunk()` fallback — set `next_chunk_id` during creation to match `chunker.py` style

**Verify:** Process a document — `steps` dict shows `docling`, `llama_index`, `bge_m3` instead of `regex_chunks`, `simple_parse`. OCR output, parsed output, chunks JSON, and embeddings all stored.

---

## Phase 4 — Search Integration

**Goal:** Hybrid search actually runs vector search (Qdrant) and graph traversal (Neo4j) alongside BM25, then merges results.

- [ ] Add `_vector_search()` to `backend/search/hybrid_search.py` — query Qdrant with embedding of query text using BGE-M3, return scored results
- [ ] Create `backend/graph/graph_searcher.py` — `search_graph(query, top_k)` function that runs Cypher traversal on Neo4j, matches entities in query text, returns connected documents
- [ ] Add `_graph_search()` to `backend/search/hybrid_search.py` — call `graph_searcher.search_graph()`, return scored results
- [ ] Update `hybrid_search()` to call all three sources: `_bm25_search()`, `_vector_search()`, `_graph_search()` — merge into single result set
- [ ] Update `source_breakdown` to reflect actual counts from each source
- [ ] Handle graceful degradation: if Qdrant/Neo4j unavailable, skip and log — `source_breakdown` shows 0 for that source

**Verify:** Search returns results with `source_breakdown.vector > 0` and `source_breakdown.graph > 0`. Source labels appear on frontend result cards.

---

## Phase 5 — BGE-Reranker

**Goal:** After merging results from BM25 + vector + graph, run neural reranker for final ordering.

- [ ] Add `_rerank_with_bge()` to `backend/search/hybrid_search.py` — uses BGE-Reranker (FlagEmbedding `bge-reranker-v2-m3` or similar) to score merged candidates against query
- [ ] Replace score-based dedup in `_merge_and_rerank()` with BGE reranker scoring — keep dedup logic, but replace `rerank_score = score` with actual reranker score
- [ ] Handle graceful degradation: if reranker deps missing, fall back to score-based merge (existing behavior)

**Verify:** Search results show `rerank_score` that differs from original `score` (proves reranker ran). Compare result ordering before/after — reranker should improve relevance.

---

## Phase 6 — Authentication

**Goal:** Protect API endpoints so only authenticated users can access the platform.

- [ ] Add JWT-based authentication middleware (`backend/auth.py`) — `/api/auth/login`, `/api/auth/refresh` endpoints
- [ ] Create `users` table in SQLite — username, hashed password, role
- [ ] Add `Depends(get_current_user)` to all API routes except health check
- [ ] Add login page and auth context to frontend — token storage, axios interceptor for Bearer token
- [ ] Protect frontend routes with auth guard — redirect to login if unauthenticated

**Verify:** Unauthenticated requests return 401. Login flow works end-to-end. Token refresh works.

---

## Phase 7 — Production Readiness

**Goal:** Docker, pagination, and deployment polish.

- [ ] Create `docker/Dockerfile.backend` and `docker/Dockerfile.frontend`
- [ ] Create `docker/docker-compose.yml` with services: backend, frontend, Qdrant, Neo4j
- [ ] Add `.env.example` with all required vars documented
- [ ] Add pagination to document listing API (`/api/documents` — `?page=1&limit=20`)
- [ ] Add frontend pagination component to documents list
- [ ] GitHub Actions CI pipeline — lint, typecheck, run tests on push

**Verify:** `docker compose up` starts full stack. Document list paginates. CI passes on push.

---

## Completed

### Phase 1-6 — Core Platform (already built)
- [x] Project initialization, FastAPI + React + Vite + Tailwind
- [x] SQLite database with documents table
- [x] Document upload API + drag & drop UI
- [x] Smart OCR detection (PyMuPDF native vs PaddleOCR)
- [x] PaddleOCR pipeline with confidence scores
- [x] Docling parsing module (headings, tables, lists)
- [x] LlamaIndex chunking module (SentenceSplitter, prev/next IDs)
- [x] Multi-format extraction (XLSX, CSV, EML, MSG, TXT, TIFF)
- [x] BGE-M3 embeddings module → Qdrant integration
- [x] Entity extraction module (LLM + regex, 10 entity types)
- [x] Neo4j knowledge graph builder (5 relationship types)
- [x] Equipment tags auto-populated from chunk text
- [x] BM25 search over processed documents
- [x] Chat assistant with RAG (citations, confidence, entities)
- [x] Chat streaming endpoint (SSE)
- [x] Search filters UI (equipment, date, type, technician, failure)
- [x] Dashboard (8 metrics, live job progress polling)
- [x] Upload page (drag & drop, multi-file queue)
- [x] Search page with functional filter UI
- [x] Chat page (conversation, confidence, sources, entities)
- [x] Document viewer (OCR text, parsed structure, entities grid, chunks)
- [x] Knowledge graph UI (vis-network interactive canvas)
- [x] Processing status page (background jobs, live progress bar)
- [x] Maintenance RCA agent (LLM + fallback)
- [x] Compliance intelligence agent (gap analysis + audit packages)
- [x] Lessons learned engine (pattern analysis + proactive warnings)
- [x] Background job system with async polling
- [x] 42 unit/API/integration tests
- [x] Mobile-responsive navigation
- [x] Externalized prompt templates (`prompts/*.txt`)
- [x] README with full documentation and quick start
