from fastapi import APIRouter, status

from . import schemas, service

router = APIRouter()


@router.post(
    "/jobs",
    response_model=schemas.Job,
    status_code=status.HTTP_201_CREATED,
)
async def post_job(req: schemas.JobCreateRequest):
    """
    Create a new mastering job.
    """
    job = await service.create_job(req)
    return job


@router.get(
    "/jobs/{job_id}",
    response_model=schemas.Job,
    status_code=status.HTTP_200_OK,
)
async def get_job(job_id: str):
    job = await service.get_job(job_id)
    return job
