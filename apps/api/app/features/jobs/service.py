from datetime import datetime

from app.core.db import db
from app.core.rabbit import publish_job
from bson import ObjectId
from fastapi import HTTPException, status

from . import schemas


async def create_job(req: schemas.JobCreateRequest) -> schemas.Job:
    job_data = req.model_dump()
    job_data["status"] = "queued"
    job_data["created_at"] = datetime.utcnow()
    job_data["updated_at"] = job_data["created_at"]

    # insert into db first so consumers can update it
    result = await db.jobs.insert_one(job_data)
    job_id = result.inserted_id

    # publish start payload for worker
    print(f"[api] publish start payload for worker {job_id}")
    await publish_job(
        {
            "type": "job.start",
            "jobId": str(job_id),
            "object_key": job_data["object_key"],
            "params": {},
        }
    )
    print(f"[api] published start payload for worker {job_id}")

    # read from db
    created_job_doc = await db.jobs.find_one({"_id": ObjectId(job_id)})
    try:
        return schemas.Job.model_validate(created_job_doc)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate job",
        )


async def get_job(job_id: str) -> schemas.Job:
    try:
        oid = ObjectId(job_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    doc = await db.jobs.find_one({"_id": oid})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return schemas.Job.model_validate(doc)
