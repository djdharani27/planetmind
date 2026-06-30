from backend.logging_config import logger

_jobs: dict = {}


def start_job_sync(job_id: str, job_type: str) -> None:
    _jobs[job_id] = {
        "job_id": job_id,
        "type": job_type,
        "status": "running",
        "progress": 0,
        "steps": {},
        "started_at": "",
        "completed_at": None,
    }


def update_progress_sync(job_id: str, step: str, status: str, progress: int) -> None:
    if job_id in _jobs:
        _jobs[job_id]["progress"] = min(progress, 100)
        _jobs[job_id]["steps"][step] = status


def complete_job_sync(job_id: str, result: dict = None) -> None:
    if job_id in _jobs:
        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["progress"] = 100
        if result:
            _jobs[job_id]["result"] = result


def fail_job_sync(job_id: str, error: str) -> None:
    if job_id in _jobs:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = error


def get_job_sync(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def get_all_jobs_sync() -> list[dict]:
    return list(_jobs.values())
