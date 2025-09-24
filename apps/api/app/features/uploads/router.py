from fastapi import APIRouter, Depends
from app.core.auth import require_user
from . import schemas, service

router = APIRouter()


@router.post("/uploads/presign", dependencies=[Depends(require_user)])
async def presign_upload(req: schemas.PresignRequest):
    result = service.create_presigned_post(
        file_name=req.file_name,
        file_type=req.file_type,
        file_size=req.file_size,
        upload_type=req.upload_type,
    )
    return result
