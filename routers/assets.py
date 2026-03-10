from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.asset import Asset
from models.user import User
from routers.auth import get_current_user
from schemas.asset_schema import AssetCreate, AssetResponse

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.post("/", response_model=AssetResponse)
def create_asset(
    data: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    asset = Asset(
        name=data.name,
        type=data.type,
        value=data.value,
        date=data.date,
        user_id=current_user.id
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/", response_model=list[AssetResponse])
def get_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(Asset)
        .filter(Asset.user_id == current_user.id)
        .order_by(Asset.date.desc(), Asset.id.desc())
        .all()
    )


@router.put("/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: int,
    data: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    asset = (
        db.query(Asset)
        .filter(Asset.id == asset_id, Asset.user_id == current_user.id)
        .first()
    )

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.name = data.name
    asset.type = data.type
    asset.value = data.value
    asset.date = data.date

    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}")
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    asset = (
        db.query(Asset)
        .filter(Asset.id == asset_id, Asset.user_id == current_user.id)
        .first()
    )

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    db.delete(asset)
    db.commit()

    return {"message": "Asset deleted successfully"}