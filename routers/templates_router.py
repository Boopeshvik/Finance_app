from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import date

from database import get_db
from models.transaction_template import TransactionTemplate
from models.transaction import Transaction
from models.category import Category
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/templates", tags=["Templates"])


class TemplateCreate(BaseModel):
    name:        str
    type:        str
    category:    str
    amount:      float
    description: Optional[str] = None
    sort_order:  Optional[int] = 0


class TemplateResponse(BaseModel):
    id:          int
    user_id:     int
    name:        str
    type:        str
    category:    str
    amount:      float
    description: Optional[str]
    sort_order:  int

    class Config:
        from_attributes = True


class ApplyTemplateRequest(BaseModel):
    month: int
    year:  int
    day:   Optional[int] = 1
    ids:   Optional[List[int]] = None  # None = apply all


# ── CRUD ──────────────────────────────────────────────────────────

@router.get("/", response_model=List[TemplateResponse])
def get_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(TransactionTemplate)
        .filter(TransactionTemplate.user_id == current_user.id)
        .order_by(TransactionTemplate.sort_order.asc(), TransactionTemplate.id.asc())
        .all()
    )


@router.post("/", response_model=TemplateResponse)
def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    t_type = data.type.strip().lower()
    if t_type not in ["income", "expense", "investment"]:
        raise HTTPException(status_code=400, detail="type must be 'income', 'expense' or 'investment'")

    template = TransactionTemplate(
        user_id     = current_user.id,
        name        = data.name.strip(),
        type        = t_type,
        category    = data.category.strip(),
        amount      = data.amount,
        description = data.description,
        sort_order  = data.sort_order or 0
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    data: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    t = db.query(TransactionTemplate).filter(
        TransactionTemplate.id == template_id,
        TransactionTemplate.user_id == current_user.id
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")

    t.name        = data.name.strip()
    t.type        = data.type.strip().lower()
    t.category    = data.category.strip()
    t.amount      = data.amount
    t.description = data.description
    t.sort_order  = data.sort_order or 0

    db.commit()
    db.refresh(t)
    return t


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    t = db.query(TransactionTemplate).filter(
        TransactionTemplate.id == template_id,
        TransactionTemplate.user_id == current_user.id
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(t)
    db.commit()
    return {"message": "Template deleted"}


# ── Apply templates ────────────────────────────────────────────────

@router.post("/apply")
def apply_templates(
    data: ApplyTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create transactions from templates for a given month"""
    uid = current_user.id

    # Get templates to apply
    query = db.query(TransactionTemplate).filter(TransactionTemplate.user_id == uid)
    if data.ids:
        query = query.filter(TransactionTemplate.id.in_(data.ids))
    templates = query.order_by(TransactionTemplate.sort_order.asc()).all()

    if not templates:
        raise HTTPException(status_code=404, detail="No templates found")

    # Build transaction date
    try:
        tx_date = date(data.year, data.month, data.day or 1)
    except ValueError:
        tx_date = date(data.year, data.month, 1)

    created = []
    skipped = []

    for t in templates:
        # Check category exists, create if not
        cat = db.query(Category).filter(
            Category.user_id == uid,
            Category.name.ilike(t.category)
        ).first()

        if not cat:
            # Auto-create category
            cat = Category(
                user_id = uid,
                name    = t.category,
                type    = t.type
            )
            db.add(cat)
            db.flush()

        # Validate category type matches
        if cat.type != t.type:
            skipped.append({
                "name":   t.name,
                "reason": f"Category '{t.category}' is type '{cat.type}', template is '{t.type}'"
            })
            continue

        # Create transaction
        tx = Transaction(
            user_id     = uid,
            type        = t.type,
            category    = t.category,
            amount      = t.amount,
            date        = tx_date,
            description = t.description or t.name
        )
        db.add(tx)
        created.append({
            "name":     t.name,
            "type":     t.type,
            "category": t.category,
            "amount":   t.amount,
        })

    db.commit()

    return {
        "message":  f"Created {len(created)} transactions for {data.month}/{data.year}",
        "created":  created,
        "skipped":  skipped,
        "count":    len(created)
    }