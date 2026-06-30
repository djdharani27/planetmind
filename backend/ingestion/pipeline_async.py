import threading
import uuid
from backend.ingestion.jobs import start_job_sync, update_progress_sync, complete_job_sync, fail_job_sync
from backend.logging_config import logger


async def process_document_async(doc_id: str, llm_client=None) -> str:
    job_id = f"process_{doc_id}_{uuid.uuid4().hex[:8]}"
    start_job_sync(job_id, "document_processing")
    t = threading.Thread(target=_run_pipeline_thread, args=(job_id, doc_id, llm_client), daemon=True)
    t.start()
    return job_id


def _run_pipeline_thread(job_id: str, doc_id: str, llm_client=None):
    try:
        update_progress_sync(job_id, "start", "running", 5)
        from backend.ingestion.pipeline import process_document
        result = process_document(doc_id, llm_client)
        if result.get("status") == "ready":
            complete_job_sync(job_id, result)
        else:
            fail_job_sync(job_id, result.get("error", "Unknown error"))
    except Exception as e:
        logger.error(f"Pipeline job {job_id} failed: {e}")
        fail_job_sync(job_id, str(e))
