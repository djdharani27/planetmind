# Architecture Decisions

## ADR-001: SQLite for Metadata Storage
**Date:** 2026-06-30
**Status:** Accepted

SQLite is used for document metadata, processing status, and pipeline state. Zero-config, no external service dependency, sufficient for MVP scale.

## ADR-002: No Docker in Phase 1
**Date:** 2026-06-30
**Status:** Accepted

Docker is excluded per explicit project requirements. Docker Compose will be added in Phase 19 (Production Readiness).

## ADR-003: Tailwind CSS 4 via Vite Plugin
**Date:** 2026-06-30
**Status:** Accepted

Using @tailwindcss/vite plugin which is the recommended approach for Tailwind CSS 4. Avoids separate PostCSS config.
