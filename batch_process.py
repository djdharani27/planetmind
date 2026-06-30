"""Bulk process all uploaded documents using lightweight pipeline."""
import json, re, fitz, sqlite3, sys, subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
db_path = BASE / "sqlite" / "planetmind.db"
uploads_dir = BASE / "storage" / "uploads"
processed_dir = BASE / "storage" / "processed"

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
docs = conn.execute("SELECT * FROM documents WHERE processing_status IN ('uploaded', 'chunking_complete')").fetchall()
conn.close()

print(f"Processing {len(docs)} documents...")

eq_re = re.compile(r"\b(WTG|Pump|Turbine|Motor|Generator|Compressor|Valve|Transformer|Gearbox)\s*[-]?\s*[A-Z0-9]{1,3}[-]?\d{2,5}\b", re.IGNORECASE)
date_re = re.compile(r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b")

for doc in docs:
    doc = dict(doc)
    fp = Path(doc["storage_path"])
    doc_id = doc["id"]
    
    ext = fp.suffix.lower()
    if ext not in (".pdf", ".txt", ".csv"):
        print(f"  SKIP {doc_id[:8]} — unsupported type: {ext}")
        continue

    try:
        if ext == ".pdf":
            pdf = fitz.open(str(fp))
            text = "\n".join(page.get_text() for page in pdf)
            pdf.close()
        elif ext == ".txt":
            text = fp.read_text(encoding="utf-8", errors="replace")
        else:
            continue

        text = text.strip()
        if not text or len(text) < 10:
            print(f"  SKIP {doc_id[:8]} — no text extracted ({len(text)} chars)")
            continue

        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks, buf = [], ""
        for s in sentences:
            if len(buf) + len(s) > 800 and buf:
                chunks.append(buf.strip()); buf = s
            else:
                buf += " " + s
        if buf.strip():
            chunks.append(buf.strip())

        entities = []
        for m in eq_re.finditer(text):
            entities.append({"type": "equipment", "value": m.group(), "confidence": 0.85})
        for m in date_re.finditer(text):
            entities.append({"type": "date", "value": m.group(), "confidence": 0.95})

        out_dir = processed_dir / doc_id
        out_dir.mkdir(parents=True, exist_ok=True)

        with open(out_dir / "ocr_output.json", "w", encoding="utf-8") as f:
            json.dump({"document_id": doc_id, "total_text": text}, f)

        chunk_objs = []
        for i, c in enumerate(chunks):
            chunk_objs.append({
                "chunk_id": f"{doc_id}_c{i}", "document_id": doc_id, "page_number": 1,
                "section": "", "chunk_text": c, "token_count": len(c.split()),
                "equipment_tags": list(set(m.group() for m in eq_re.finditer(c)))[:5],
            })
        with open(out_dir / "chunks.json", "w", encoding="utf-8") as f:
            json.dump(chunk_objs, f)
        with open(out_dir / "entities.json", "w", encoding="utf-8") as f:
            json.dump(entities, f)

        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "UPDATE documents SET processing_status = ?, metadata = ? WHERE id = ?",
            ("ready", json.dumps({"text_length": len(text), "chunks": len(chunks), "entities": len(entities)}), doc_id),
        )
        conn.commit()
        conn.close()

        print(f"  OK {doc_id[:8]} {doc['filename']}: {len(text)} chars, {len(chunks)} chunks, {len(entities)} entities")

    except Exception as e:
        print(f"  FAIL {doc_id[:8]} {doc['filename']}: {e}")
        conn = sqlite3.connect(str(db_path))
        conn.execute("UPDATE documents SET processing_status = ? WHERE id = ?", ("failed", doc_id))
        conn.commit()
        conn.close()

print("BATCH COMPLETE")
