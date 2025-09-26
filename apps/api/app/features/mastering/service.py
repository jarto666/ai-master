from __future__ import annotations

from datetime import datetime, timezone

from app.core.db import SessionLocal
from app.core.rabbit import publish_job
from app.features.assets.entities import Asset
from app.features.mastering.entities import Job
from fastapi import HTTPException, status
from sqlalchemy import insert, select

from . import dto


async def list_jobs(*, user_id: str) -> list[dto.MasteringJob]:
    async with SessionLocal() as session:
        res = await session.execute(
            select(Job).where(Job.user_id == user_id).order_by(Job.created_at.desc())
        )
        rows = res.scalars().all()
        out: list[dto.MasteringJob] = []
        for j in rows:
            out.append(
                dto.MasteringJob.model_validate(
                    {
                        "id": str(j.id),
                        "userId": str(j.user_id),
                        "inputAssetId": str(j.input_asset_id),
                        "referenceAssetId": str(j.reference_asset_id)
                        if j.reference_asset_id
                        else None,
                        "object_key": j.object_key,
                        "reference_object_key": j.reference_object_key,
                        "status": j.status,
                        "result_object_key": j.result_object_key,
                        "preview_object_key": j.preview_object_key,
                        "lastError": j.last_error,
                        "created_at": j.created_at,
                        "updated_at": j.updated_at,
                    }
                )
            )
        return out


async def start_mastering(
    *, req: dto.StartMasteringRequest, user_id: str
) -> dto.MasteringJob:
    async with SessionLocal() as session:
        res = await session.execute(
            select(Asset).where(Asset.id == req.asset_id, Asset.user_id == user_id)
        )
        asset = res.scalar_one_or_none()
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
            )
        if asset.status != "uploaded":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Asset not uploaded yet"
            )

        reference_object_key: str | None = None
        reference_asset_id: str | None = None
        if req.reference_asset_id:
            res2 = await session.execute(
                select(Asset).where(
                    Asset.id == req.reference_asset_id, Asset.user_id == user_id
                )
            )
            ref_asset = res2.scalar_one_or_none()
            if not ref_asset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Reference asset not found",
                )
            if ref_asset.status != "uploaded":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reference asset not uploaded yet",
                )
            reference_object_key = ref_asset.s3_key
            reference_asset_id = str(ref_asset.id)

        now = datetime.now(timezone.utc)
        ins = (
            insert(Job)
            .values(
                user_id=user_id,
                input_asset_id=str(asset.id),
                reference_asset_id=reference_asset_id,
                object_key=asset.s3_key,
                reference_object_key=reference_object_key,
                status="queued",
                result_object_key=None,
                preview_object_key=None,
                created_at=now,
                updated_at=now,
            )
            .returning(Job)
        )
        res3 = await session.execute(ins)
        job = res3.scalar_one()
        await session.commit()

        await publish_job(
            {
                "type": "job.start",
                "jobId": str(job.id),
                "object_key": job.object_key,
                "params": {},
            }
        )

        return dto.MasteringJob.model_validate(
            {
                "id": str(job.id),
                "userId": str(job.user_id),
                "inputAssetId": str(job.input_asset_id),
                "referenceAssetId": str(job.reference_asset_id)
                if job.reference_asset_id
                else None,
                "object_key": job.object_key,
                "reference_object_key": job.reference_object_key,
                "status": job.status,
                "result_object_key": job.result_object_key,
                "preview_object_key": job.preview_object_key,
                "lastError": job.last_error,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            }
        )


async def get_status(*, job_id: str, user_id: str) -> dto.MasteringJob:
    async with SessionLocal() as session:
        res = await session.execute(
            select(Job).where(Job.id == job_id, Job.user_id == user_id)
        )
        j: Job | None = res.scalar_one_or_none()
        if not j:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
            )
        return dto.MasteringJob.model_validate(
            {
                "id": str(j.id),
                "userId": str(j.user_id),
                "inputAssetId": str(j.input_asset_id),
                "referenceAssetId": str(j.reference_asset_id)
                if j.reference_asset_id
                else None,
                "object_key": j.object_key,
                "reference_object_key": j.reference_object_key,
                "status": j.status,
                "result_object_key": j.result_object_key,
                "preview_object_key": j.preview_object_key,
                "lastError": j.last_error,
                "created_at": j.created_at,
                "updated_at": j.updated_at,
            }
        )
