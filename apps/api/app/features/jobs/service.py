from bson import ObjectId
from app.core.db import db
from app.core.rabbit import publish_job
from . import schemas


async def create_job(req: schemas.JobCreateRequest) -> schemas.Job:
    job_data = req.model_dump()
    job_data["status"] = "queued"
    
    # insert into db
    result = await db.jobs.insert_one(job_data)
    job_id = result.inserted_id

    # publish to queue
    await publish_job({"jobId": str(job_id)})

    # read from db
    created_job_doc = await db.jobs.find_one({"_id": ObjectId(job_id)})
    return schemas.Job.model_validate(created_job_doc)
