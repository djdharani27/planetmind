# PlanetMind AI — Architecture

## Overview

PlanetMind AI is an industrial intelligence platform that ingests technical documents (PDFs, DOCX, images), processes them through OCR, parsing, chunking, embedding, entity extraction, and knowledge graph construction, then provides AI-powered chat and hybrid search over the processed data.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 6, Tailwind CSS 4 |
| Backend | FastAPI (Python) |
| Database (metadata) | SQLite |
| Vector Store | Qdrant |
| Graph Database | Neo4j |
| OCR | PaddleOCR |
| Parsing | Docling |
| Chunking | LlamaIndex Node Parser |
| Embeddings | BGE-M3 (BAAI) |
| LLM | Configurable (OpenAI-compatible API) |
| Search | BM25 + Vector + Graph → BGE-Reranker |

## Folder Structure

```
planetmind/
├── backend/
│   ├── api/              # FastAPI routes
│   ├── ingestion/        # OCR, Docling, Chunking
│   ├── embeddings/       # BGE-M3 embedding generation
│   ├── search/           # Hybrid search (BM25, vector, graph)
│   ├── graph/            # Neo4j knowledge graph
│   ├── llm/              # LLM interface
│   ├── database/         # SQLite
│   ├── models/           # Pydantic models
│   └── utils/            # Shared utilities
├── frontend/
│   ├── src/pages/
│   ├── src/components/
│   └── src/hooks/
├── storage/
│   ├── uploads/
│   ├── processed/
│   └── cache/
├── prompts/              # LLM prompt templates
└── data/                 # Seed/config data
```

## Development Phases

See `track.md` for current progress and `tasks.md` for detailed task tracking.
