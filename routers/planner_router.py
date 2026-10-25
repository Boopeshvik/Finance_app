from calendar import monthrange
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.planned_item import PlannedItem
from models.transaction import Transaction
from models.transaction_template import TransactionTemplate
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/planner", tags=["Planner"])

VALID_TYPES = ["income", "expense", "investment"]


class PlannedItemIn(BaseModel):
    date:        date
    type:        str
    category:    str
    amount:      float
    description: Optional[str] = None


class ApplyTemplatesIn(BaseModel):
    date: date
    ids:  List[int]


def _out(p: PlannedItem):
    return {"id": p.id, "date": p.date.isoformat(), "type": p.type, "category": p.category,
            "amount": p.amount, "description": p.description, "status": p.status}


def _validate(data: PlannedItemIn):
    if data.type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="type must be income, expense or investment")
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be greater than 0")
    if not data.category.strip():
        raise HTTPException(status_code=400, detail="category is required")


@router.get("/{year}/{month}")
def get_month(year: int, month: int, db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="invalid month")
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    items = (db.query(PlannedItem)
             .filter(PlannedItem.user_id == current_user.id, PlannedItem.date >= start, PlannedItem.date <= end)
             .order_by(PlannedItem.date, PlannedItem.id).all())
    return [_out(p) for p in items]


@router.post("")
def create_item(data: PlannedItemIn, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    _validate(data)
    p = PlannedItem(user_id=current_user.id, date=data.date, type=data.type,
                    category=data.category.strip(), amount=data.amount,
                    description=data.description, status="planned")
    db.add(p); db.commit(); db.refresh(p)
    return _out(p)


@router.put("/{item_id}")
def update_item(item_id: int, data: PlannedItemIn, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    _validate(data)
    p = db.query(PlannedItem).filter(PlannedItem.id == item_id, PlannedItem.user_id == current_user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Planned item not found")
    p.date = data.date; p.type = data.type; p.category = data.category.strip()
    p.amount = data.amount; p.description = data.description
    db.commit(); db.refresh(p)
    return _out(p)


@router.delete("/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    p = db.query(PlannedItem).filter(PlannedItem.id == item_id, PlannedItem.user_id == current_user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Planned item not found")
    db.delete(p); db.commit()
    return {"message": "deleted"}


@router.post("/{item_id}/complete")
def complete_item(item_id: int, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    """Turn a planned item into a real transaction."""
    p = db.query(PlannedItem).filter(PlannedItem.id == item_id, PlannedItem.user_id == current_user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Planned item not found")
    if p.status == "done":
        raise HTTPException(status_code=400, detail="Already marked as done")
    db.add(Transaction(user_id=current_user.id, type=p.type, category=p.category,
                       amount=p.amount, date=p.date, description=p.description))
    p.status = "done"
    db.commit(); db.refresh(p)
    return _out(p)


@router.post("/apply-templates")
def apply_templates(data: ApplyTemplatesIn, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    """Copy chosen monthly templates onto a date as planned items."""
    tpls = (db.query(TransactionTemplate)
            .filter(TransactionTemplate.user_id == current_user.id, TransactionTemplate.id.in_(data.ids)).all())
    created = []
    for t in tpls:
        p = PlannedItem(user_id=current_user.id, date=data.date, type=t.type, category=t.category,
                        amount=t.amount, description=t.description or t.name, status="planned")
        db.add(p); created.append(p)
    db.commit()
    return {"created": len(created)}