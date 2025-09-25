from __future__ import annotations

from app.core.auth import require_user
from fastapi import APIRouter, Request, status

from . import schemas, service

router = APIRouter()


def _get_user_id(request: Request) -> str:
    claims = require_user(request)
    return str(claims.get("id"))


@router.post(
    "/mastering/start",
    response_model=schemas.MasteringJob,
    status_code=status.HTTP_201_CREATED,
)
async def start_mastering(req: schemas.StartMasteringRequest, request: Request):
    user_id = _get_user_id(request)
    return await service.start_mastering(req=req, user_id=user_id)


@router.get(
    "/mastering/{job_id}",
    response_model=schemas.MasteringJob,
    status_code=status.HTTP_200_OK,
)
async def get_mastering_status(job_id: str, request: Request):
    user_id = _get_user_id(request)
    return await service.get_status(job_id=job_id, user_id=user_id)
