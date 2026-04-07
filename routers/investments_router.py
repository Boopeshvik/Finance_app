from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models.investment import Investment
from models.user import User
from routers.auth import get_current_user
from schemas.investment_schema import InvestmentCreate, InvestmentUpdate, InvestmentResponse

router = APIRouter(prefix="/investments", tags=["Investments"])


@router.post("/", response_model=InvestmentResponse)
def create_investment(
    data: InvestmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    investment = Investment(
        user_id         = current_user.id,
        name            = data.name.strip(),
        month           = data.month,
        year            = data.year,
        amount_invested = data.amount_invested,
        current_value   = data.current_value,
        notes           = data.notes
    )
    db.add(investment)
    db.commit()
    db.refresh(investment)
    return investment


@router.get("/", response_model=list[InvestmentResponse])
def get_investments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(Investment)
        .filter(Investment.user_id == current_user.id)
        .order_by(Investment.year.desc(), Investment.month.desc(), Investment.name.asc())
        .all()
    )


@router.put("/{investment_id}", response_model=InvestmentResponse)
def update_investment(
    investment_id: int,
    data: InvestmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    inv = db.query(Investment).filter(
        Investment.id == investment_id,
        Investment.user_id == current_user.id
    ).first()

    if not inv:
        raise HTTPException(status_code=404, detail="Investment not found")

    inv.name            = data.name.strip()
    inv.month           = data.month
    inv.year            = data.year
    inv.amount_invested = data.amount_invested
    inv.current_value   = data.current_value
    inv.notes           = data.notes

    db.commit()
    db.refresh(inv)
    return inv


@router.delete("/{investment_id}")
def delete_investment(
    investment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    inv = db.query(Investment).filter(
        Investment.id == investment_id,
        Investment.user_id == current_user.id
    ).first()

    if not inv:
        raise HTTPException(status_code=404, detail="Investment not found")

    db.delete(inv)
    db.commit()
    return {"message": "Investment deleted"}