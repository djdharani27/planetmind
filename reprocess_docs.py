import requests, sys, time

TOKEN = sys.argv[1]
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

resp = requests.get("http://localhost:8000/api/documents", headers=headers)
docs = resp.json()["documents"]
to_process = [d for d in docs if d["processing_status"] in ("ready", "ocr_complete", "parsing_complete", "chunking_complete")][:4]
print(f"Reprocessing {len(to_process)} documents")

for doc in to_process:
    doc_id = doc["id"]
    resp = requests.post(
        "http://localhost:8000/api/pipeline/process-async",
        headers=headers,
        json={"document_id": doc_id},
    )
    if resp.ok:
        print(f"  Queued: {doc['filename'][:40]} -> {resp.json()['job_id'][-12:]}")
    else:
        print(f"  Failed: {resp.text[:80]}")
    time.sleep(2)
