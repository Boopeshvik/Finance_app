from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models.asset import Asset
from models.liability import Liability

router = APIRouter(prefix="/networth", tags=["Net Worth"])


@router.get("/current")
def get_current_networth(db: Session = Depends(get_db)):
    latest_asset_date = db.query(func.max(Asset.date)).scalar()
    latest_liability_date = db.query(func.max(Liability.date)).scalar()

    total_assets = 0
    total_liabilities = 0

    if latest_asset_date:
        total_assets = (
            db.query(func.coalesce(func.sum(Asset.value), 0))
            .filter(Asset.date == latest_asset_date)
            .scalar()
        )

    if latest_liability_date:
        total_liabilities = (
            db.query(func.coalesce(func.sum(Liability.amount), 0))
            .filter(Liability.date == latest_liability_date)
            .scalar()
        )

    return {
        "asset_snapshot_date": latest_asset_date,
        "liability_snapshot_date": latest_liability_date,
        "total_assets": round(total_assets, 2),
        "total_liabilities": round(total_liabilities, 2),
        "networth": round(total_assets - total_liabilities, 2)
    }


@router.get("/history")
def get_networth_history(db: Session = Depends(get_db)):
    asset_dates = [row[0] for row in db.query(Asset.date).distinct().all()]
    liability_dates = [row[0] for row in db.query(Liability.date).distinct().all()]

    all_dates = sorted(set(asset_dates + liability_dates))

    history = []

    for snapshot_date in all_dates:
        total_assets = (
            db.query(func.coalesce(func.sum(Asset.value), 0))
            .filter(Asset.date == snapshot_date)
            .scalar()
        )

        total_liabilities = (
            db.query(func.coalesce(func.sum(Liability.amount), 0))
            .filter(Liability.date == snapshot_date)
            .scalar()
        )

        history.append({
            "date": snapshot_date,
            "total_assets": round(total_assets, 2),
            "total_liabilities": round(total_liabilities, 2),
            "networth": round(total_assets - total_liabilities, 2)
        })

    return history