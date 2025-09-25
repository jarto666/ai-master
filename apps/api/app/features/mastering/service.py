from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.core.db import db
from app.core.rabbit import publish_job
from bson import ObjectId
from fastapi import HTTPException, status

from . import schemas


async def list_jobs(*, user_id: str) -> list[schemas.MasteringJob]:
    cursor = db.jobs.find({"userId": user_id}).sort("created_at", -1)
    results: list[schemas.MasteringJob] = []
    async for doc in cursor:
        try:
            results.append(schemas.MasteringJob.model_validate(doc))
        except Exception:
            continue
    return results


async def start_mastering(
    *, req: schemas.StartMasteringRequest, user_id: str
) -> schemas.MasteringJob:
    try:
        input_oid = ObjectId(req.asset_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )

    asset = await db.assets.find_one({"_id": input_oid, "userId": user_id})
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )
    if asset.get("status") != "uploaded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Asset not uploaded yet"
        )

    reference_object_key: str | None = None
    reference_asset_id: str | None = None
    if req.reference_asset_id:
        try:
            ref_oid = ObjectId(req.reference_asset_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reference asset not found",
            )
        ref_asset = await db.assets.find_one({"_id": ref_oid, "userId": user_id})
        if not ref_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reference asset not found",
            )
        if ref_asset.get("status") != "uploaded":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference asset not uploaded yet",
            )
        reference_object_key = ref_asset.get("object_key")
        reference_asset_id = str(ref_asset.get("_id"))

    job_data: Dict[str, Any] = {
        "userId": user_id,
        "inputAssetId": str(asset["_id"]),
        "referenceAssetId": reference_asset_id,
        "object_key": asset["object_key"],
        "reference_object_key": reference_object_key,
        "status": "queued",
        "result_object_key": None,
        "preview_object_key": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    result = await db.jobs.insert_one(job_data)
    job_id = result.inserted_id

    await publish_job(
        {
            "type": "job.start",
            "jobId": str(job_id),
            "object_key": job_data["object_key"],
            "params": {},
        }
    )

    created = await db.jobs.find_one({"_id": ObjectId(job_id)})
    return schemas.MasteringJob.model_validate(created)


async def get_status(*, job_id: str, user_id: str) -> schemas.MasteringJob:
    try:
        oid = ObjectId(job_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    doc = await db.jobs.find_one({"_id": oid, "userId": user_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return schemas.MasteringJob.model_validate(doc)


# async def create_job(req: schemas.JobCreateRequest) -> schemas.Job:
#     job_data = req.model_dump()
#     job_data["status"] = "queued"
#     job_data["created_at"] = datetime.utcnow()
#     job_data["updated_at"] = job_data["created_at"]

#     # insert into db first so consumers can update it
#     result = await db.jobs.insert_one(job_data)
#     job_id = result.inserted_id

#     # publish start payload for worker
#     print(f"[api] publish start payload for worker {job_id}")
#     await publish_job(
#         {
#             "type": "job.start",
#             "jobId": str(job_id),
#             "object_key": job_data["object_key"],
#             "params": {},
#         }
#     )
#     print(f"[api] published start payload for worker {job_id}")

#     # read from db
#     created_job_doc = await db.jobs.find_one({"_id": ObjectId(job_id)})
#     try:
#         return schemas.Job.model_validate(created_job_doc)
#     except Exception:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to validate job",
#         )


# async def get_job(job_id: str) -> schemas.Job:
#     try:
#         oid = ObjectId(job_id)
#     except Exception:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
#         )

#     doc = await db.jobs.find_one({"_id": oid})
#     if not doc:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
#         )
#     return schemas.Job.model_validate(doc)
