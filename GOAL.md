MVP Features
1. Document Upload
User can upload
PDFs
DOCX
Images
Scanned manuals
Maintenance reports
SOPs
Incident reports
2. OCR Pipeline
Upload Document
        │
        ▼
PaddleOCR
        │
        ▼
Extract Text
        │
        ▼
Save Raw OCR Output

Output

Extracted text
Page numbers
Confidence score
3. Document Parsing

Using Docling

Extract

Headings
Paragraphs
Tables
Images
Lists
Page structure

Result

Document

├── Page 1
│     ├── Heading
│     ├── Table
│     ├── Paragraph
│
├── Page 2
│     ├── Heading
│     ├── Image
│     ├── Paragraph
4. Intelligent Chunking

Using LlamaIndex Node Parser

Chunk by

Heading
Section
Token limit

Each chunk stores

Chunk ID

Document ID

Page Number

Section

Chunk Text

Metadata
5. Embedding Generation

Model

BAAI BGE-M3

Generate embedding for every chunk.

Store inside

Qdrant
6. Entity Extraction

Use LLM.

Extract

Equipment

Pump

Valve

Motor

Transformer

Wind Turbine

Failure

Incident

Technician

Date

Location

Regulation

Maintenance Activity

Example

Pump P-204

↓

Bearing Failure

↓

Repaired by John

↓

2024-03-14
7. Knowledge Graph Construction

Store in Neo4j

Example

Pump P-204

        │

HAS_FAILURE

        │

Bearing Failure

        │

FIXED_BY

        │

John

        │

RECORDED_IN

        │

Maintenance Report
8. Hybrid Search

When user asks

Why did Pump P-204 fail?

Search runs

Keyword Search

+

Vector Search

+

Graph Traversal

BM25

↓

Equipment ID

Qdrant

↓

Similar maintenance reports

Neo4j

↓

Connected failures

Merge

↓

Rerank

↓

LLM

9. AI Chat Assistant

User asks

Show previous gearbox failures.

LLM receives

Top Vector Results

+

Graph Relationships

+

Keyword Matches

Returns

Answer

+

Document Citations

+

Page Numbers

Example

Gearbox failures occurred 3 times.

Root cause:

• Lubrication contamination

• Misalignment

• Overheating

Sources

Maintenance Report 2024
Page 18

Inspection Report
Page 7
Complete Processing Pipeline
Document Upload

        │

        ▼

PaddleOCR

        │

        ▼

Docling Parsing

        │

        ▼

Chunking

        │

        ▼

Embeddings

        │

        ├────────► Qdrant

        │

        ▼

LLM Entity Extraction

        │

        ▼

Neo4j Graph

        │

        ▼

Ready for Search
User Query Pipeline
User Question

        │

        ▼

Intent Detection

        │

        ▼

Parallel Search

        │

 ┌───────────────┬──────────────┬─────────────┐
 │               │              │
 ▼               ▼              ▼

BM25         Qdrant        Neo4j

 │               │              │

 └───────────────┴──────────────┘

        │

        ▼

Merge Results

        │

        ▼

BGE-Reranker

        │

        ▼

Context Builder

        │

        ▼

LLM

        │

        ▼

Answer + Citations
MVP UI
1. Dashboard

Displays

Documents Uploaded
Chunks Created
Entities Extracted
Relationships
Search Statistics
2. Upload Screen
Drag & Drop

Choose File

Processing Status

OCR Progress

Embedding Progress

Completed
3. Document Viewer

Shows

Original PDF
OCR text
Extracted metadata
Extracted entities
4. Chat Screen
Ask anything...

---------------------------------

Why did Turbine WTG-12 fail?

---------------------------------

AI Answer

Sources

Maintenance.pdf

Page 16

Incident.pdf

Page 4
5. Knowledge Graph

Interactive graph

Pump

↓

Failure

↓

Maintenance

↓

Technician

↓

Document

Clicking any node opens related documents.

6. Search Page

Search

gearbox inspection

Returns

Documents

Similarity

Related Equipment

Related Failures

Preview
Folder Structure
industrial-ai/

│

├── backend/
│   ├── api/
│   ├── ingestion/
│   │   ├── paddleocr/
│   │   ├── docling/
│   │   ├── chunking/
│   ├── embeddings/
│   ├── search/
│   ├── graph/
│   ├── llm/
│   ├── database/
│   ├── models/
│   └── utils/
│
├── frontend/
│   ├── pages/
│   ├── components/
│   └── hooks/
│
├── uploads/
├── processed/
├── qdrant/
├── sqlite/
├── prompts/
├── docker/
└── data/

1. Smart OCR Decision (under OCR Pipeline)
Detect whether the document is scanned or digitally searchable.
Use PaddleOCR only for scanned PDFs/images.
Extract native text directly from searchable PDFs.
2. Additional Metadata (under Document Upload)

Store:

Document ID
File Name
File Type
Upload Timestamp
Processing Status
3. Additional Chunk Metadata (under Intelligent Chunking)

Each chunk also stores:

Previous Chunk ID
Next Chunk ID
Equipment Tags (if available)
4. Simplified Entity Types (under Entity Extraction)

Focus on high-value entities:

Equipment
Component
Failure
Maintenance Activity
Technician
Date
Location
Regulation
Document
Process Parameter

Note: Entity resolution/deduplication is out of MVP scope.

5. Simplified Knowledge Graph (under Knowledge Graph)

Primary relationships only:

HAS_FAILURE
FIXED_BY
RECORDED_IN
MENTIONS
LOCATED_AT (optional)
6. Search Output (under Hybrid Search)

Return:

Top Ranked Chunks
Related Equipment
Related Failures
Related Maintenance Records
7. Confidence Score (under AI Chat Assistant)

Include:

Answer Confidence Score (e.g., 92%)
Source Citations
Page Numbers
8. Processing Status Screen (under Upload Screen)

Show pipeline progress:

Upload Complete
OCR Complete
Parsing Complete
Chunking Complete
Embeddings Generated
Entities Extracted
Knowledge Graph Updated
Ready for Search
9. Document Viewer Enhancements

Also display:

Parsed Document Structure
Chunk Boundaries
10. Search Filters (under Search Page)

Add filters:

Equipment
Date
Document Type
Technician
Failure Type
11. Dashboard Metrics

Add:

Graph Nodes
Processing Success Rate
Average Search Time
12. Folder Structure

Instead of:

uploads/
processed/

Use:

storage/
├── uploads/
├── processed/
├── cache/