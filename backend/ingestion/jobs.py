import asyncio
from backend.logging_config import logger

_jobs: dict = {}
_lock = asyncio.Lock()


async def start_job(job_id: str, job_type: str) -> None:
    async with _lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "type": job_type,
            "status": "running",
            "progress": 0,
            "steps": {},
            "started_at": "",
            "completed_at": None,
        }


async def update_progress(job_id: str, step: str, status: str, progress: int) -> None:
    async with _lock:
        if job_id in _jobs:
            _jobs[job_id]["progress"] = min(progress, 100)
            _jobs[job_id]["steps"][step] = status
            logger.debug(f"Job {job_id}: {step} → {status} ({progress}%)")


async def complete_job(job_id: str, result: dict = None) -> None:
    async with _lock:
        if job_id in _jobs:
            _jobs[job_id]["status"] = "completed"
            _jobs[job_id]["progress"] = 100
            if result:
                _jobs[job_id]["result"] = result


async def fail_job(job_id: str, error: str) -> None:
    async with _lock:
        if job_id in _jobs:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = error


async def get_job(job_id: str) -> dict | None:
    async with _lock:
        return _jobs.get(job_id)


async def get_all_jobs() -> list[dict]:
    async with _lock:
        return list(_jobs.values())
