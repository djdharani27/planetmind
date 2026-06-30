import json, re, fitz, sqlite3, os, sys
from pathlib import Path

doc_id = sys.argv[1] if len(sys.argv) > 1 else None
if not doc_id:
    docs = os.listdir("storage/uploads")
    print("Available doc IDs:", docs[:5])
    sys.exit(0)

BASE = Path(__file__).resolve().parent
db_path = BASE / "sqlite" / "planetmind.db"
uploads_dir = BASE / "storage" / "uploads"
processed_dir = BASE / "storage" / "processed"

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
doc = dict(conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone())
conn.close()

fp = Path(doc["storage_path"])
if not fp.exists():
    print(f"File not found: {fp}")
    sys.exit(1)

print(f"Document: {doc['filename']} ({doc['file_type']})")

pdf = fitz.open(str(fp))
text = "\n".join(page.get_text() for page in pdf)
pdf.close()
print(f"Text extracted: {len(text)} chars")

sentences = re.split(r"(?<=[.!?])\s+", text)
chunks, buf = [], ""
for s in sentences:
    if len(buf) + len(s) > 800 and buf:
        chunks.append(buf.strip()); buf = s
    else:
        buf += " " + s
if buf.strip():
    chunks.append(buf.strip())
print(f"Chunks: {len(chunks)}")

eq_re = re.compile(r"\b(WTG|Pump|Turbine|Motor|Generator|Compressor|Valve|Transformer|Gearbox)\s*[-]?\s*[A-Z0-9]{1,3}[-]?\d{2,5}\b", re.IGNORECASE)
date_re = re.compile(r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b")
entities = []
for m in eq_re.finditer(text):
    entities.append({"type": "equipment", "value": m.group(), "confidence": 0.85})
for m in date_re.finditer(text):
    entities.append({"type": "date", "value": m.group(), "confidence": 0.95})
print(f"Entities: {len(entities)}")

out_dir = processed_dir / doc_id
out_dir.mkdir(parents=True, exist_ok=True)

ocr_data = {"document_id": doc_id, "total_text": text, "pages": [{"page_number": 1, "text": text, "confidence": 1.0}]}
with open(out_dir / "ocr_output.json", "w", encoding="utf-8") as f:
    json.dump(ocr_data, f, ensure_ascii=False, indent=2)

chunk_objs = []
for i, c in enumerate(chunks):
    chunk_objs.append({
        "chunk_id": f"{doc_id}_c{i}",
        "document_id": doc_id,
        "page_number": 1,
        "section": "",
        "chunk_text": c,
        "token_count": len(c.split()),
        "previous_chunk_id": f"{doc_id}_c{i-1}" if i > 0 else None,
        "next_chunk_id": f"{doc_id}_c{i+1}" if i < len(chunks) - 1 else None,
        "equipment_tags": list(set(m.group() for m in eq_re.finditer(c)))[:5],
    })
with open(out_dir / "chunks.json", "w", encoding="utf-8") as f:
    json.dump(chunk_objs, f, ensure_ascii=False, indent=2)

with open(out_dir / "entities.json", "w", encoding="utf-8") as f:
    json.dump(entities, f, ensure_ascii=False, indent=2)

sections = []
for line in text.split("\n")[:50]:
    if re.match(r"^[A-Z][A-Za-z\s\-/]{3,50}$", line.strip()):
        sections.append({"heading": line.strip(), "level": 1, "paragraphs": [], "tables": []})
with open(out_dir / "parsed_output.json", "w", encoding="utf-8") as f:
    json.dump({"document_id": doc_id, "sections": sections}, f, ensure_ascii=False, indent=2)

conn = sqlite3.connect(str(db_path))
conn.execute(
    "UPDATE documents SET processing_status = ?, metadata = ? WHERE id = ?",
    ("ready", json.dumps({"text_length": len(text), "chunks": len(chunks), "entities": len(entities)}), doc_id),
)
conn.commit()
conn.close()

print(f"DONE — {len(text)} chars, {len(chunks)} chunks, {len(entities)} entities → READY")
