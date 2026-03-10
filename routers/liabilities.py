from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.liability import Liability
from models.user import User
from routers.auth import get_current_user
from schemas.liability_schema import LiabilityCreate, LiabilityResponse

router = APIRouter(prefix="/liabilities", tags=["Liabilities"])


@router.post("/", response_model=LiabilityResponse)
def create_liability(
    data: LiabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    liability = Liability(
        name=data.name,
        type=data.type,
        amount=data.amount,
        date=data.date,
        user_id=current_user.id
    )
    db.add(liability)
    db.commit()
    db.refresh(liability)
    return liability


@router.get("/", response_model=list[LiabilityResponse])
def get_liabilities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(Liability)
        .filter(Liability.user_id == current_user.id)
        .order_by(Liability.date.desc(), Liability.id.desc())
        .all()
    )


@router.put("/{liability_id}", response_model=LiabilityResponse)
def update_liability(
    liability_id: int,
    data: LiabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    liability = (
        db.query(Liability)
        .filter(Liability.id == liability_id, Liability.user_id == current_user.id)
        .first()
    )

    if not liability:
        raise HTTPException(status_code=404, detail="Liability not found")

    liability.name = data.name
    liability.type = data.type
    liability.amount = data.amount
    liability.date = data.date

    db.commit()
    db.refresh(liability)
    return liability


@router.delete("/{liability_id}")
def delete_liability(
    liability_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    liability = (
        db.query(Liability)
        .filter(Liability.id == liability_id, Liability.user_id == current_user.id)
        .first()
    )

    if not liability:
        raise HTTPException(status_code=404, detail="Liability not found")

    db.delete(liability)
    db.commit()

    return {"message": "Liability deleted successfully"}