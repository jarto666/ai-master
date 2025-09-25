from __future__ import annotations

from app.core.auth import require_user
from fastapi import APIRouter, Request, status

from . import schemas, service

router = APIRouter()


def _get_user_id(request: Request) -> str:
    claims = require_user(request)
    return str(claims.get("id"))


@router.get(
    "/assets",
    response_model=list[schemas.Asset],
    status_code=status.HTTP_200_OK,
)
async def list_assets(request: Request):
    user_id = _get_user_id(request)
    return await service.list_assets(user_id=user_id)


@router.post(
    "/assets",
    response_model=schemas.AssetCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_asset(req: schemas.AssetCreateRequest, request: Request):
    user_id = _get_user_id(request)
    return await service.create_asset(req=req, user_id=user_id)


@router.post(
    "/assets/{asset_id}/confirm",
    response_model=schemas.Asset,
    status_code=status.HTTP_200_OK,
)
async def confirm_asset_upload(
    asset_id: str, req: schemas.AssetConfirmRequest, request: Request
):
    user_id = _get_user_id(request)
    return await service.confirm_upload(asset_id=asset_id, user_id=user_id, req=req)


@router.get(
    "/assets/{asset_id}",
    response_model=schemas.Asset,
    status_code=status.HTTP_200_OK,
)
async def get_asset(asset_id: str, request: Request):
    user_id = _get_user_id(request)
    return await service.get_asset(asset_id=asset_id, user_id=user_id)
