from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.investment import Investment, InvestmentHistory
from models.user import User
from routers.auth import get_current_user
from schemas.investment_schema import (
    InvestmentCreate, InvestmentUpdate, InvestmentResponse,
    HistoryCreate, HistoryResponse
)

router = APIRouter(prefix="/investments", tags=["Investments"])


# ── Investments CRUD ─────────────────────────────────────────────

@router.post("/", response_model=InvestmentResponse)
def create_investment(
    data: InvestmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check for duplicate name
    existing = db.query(Investment).filter(
        Investment.user_id == current_user.id,
        Investment.name == data.name.strip()
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Investment '{data.name}' already exists. Use the history endpoint to add monthly updates.")

    inv = Investment(
        user_id        = current_user.id,
        name           = data.name.strip(),
        start_date     = data.start_date,
        total_invested = data.total_invested,
        current_value  = data.current_value,
        notes          = data.notes
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


@router.get("/", response_model=List[InvestmentResponse])
def get_investments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(Investment)
        .filter(Investment.user_id == current_user.id)
        .order_by(Investment.name.asc())
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

    inv.name           = data.name.strip()
    inv.start_date     = data.start_date
    inv.total_invested = data.total_invested
    inv.current_value  = data.current_value
    inv.notes          = data.notes

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

    # Delete history too
    db.query(InvestmentHistory).filter(
        InvestmentHistory.investment_id == investment_id
    ).delete()

    db.delete(inv)
    db.commit()
    return {"message": "Investment and all history deleted"}


# ── Investment History ────────────────────────────────────────────

@router.post("/{investment_id}/history", response_model=HistoryResponse)
def add_history(
    investment_id: int,
    data: HistoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    inv = db.query(Investment).filter(
        Investment.id == investment_id,
        Investment.user_id == current_user.id
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investment not found")

    # Check duplicate month/year for this investment
    existing = db.query(InvestmentHistory).filter(
        InvestmentHistory.investment_id == investment_id,
        InvestmentHistory.month == data.month,
        InvestmentHistory.year == data.year
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"History entry for {data.month}/{data.year} already exists. Use PUT to update it.")

    history = InvestmentHistory(
        investment_id = investment_id,
        user_id       = current_user.id,
        month         = data.month,
        year          = data.year,
        amount_added  = data.amount_added,
        current_value = data.current_value,
        note          = data.note
    )
    db.add(history)

    # Update parent investment totals
    inv.total_invested += data.amount_added
    inv.current_value   = data.current_value  # always use latest

    db.commit()
    db.refresh(history)
    return history


@router.get("/{investment_id}/history", response_model=List[HistoryResponse])
def get_history(
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

    return (
        db.query(InvestmentHistory)
        .filter(InvestmentHistory.investment_id == investment_id)
        .order_by(InvestmentHistory.year.asc(), InvestmentHistory.month.asc())
        .all()
    )


@router.put("/{investment_id}/history/{history_id}", response_model=HistoryResponse)
def update_history(
    investment_id: int,
    history_id: int,
    data: HistoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    hist = db.query(InvestmentHistory).filter(
        InvestmentHistory.id == history_id,
        InvestmentHistory.investment_id == investment_id,
        InvestmentHistory.user_id == current_user.id
    ).first()
    if not hist:
        raise HTTPException(status_code=404, detail="History entry not found")

    old_amount = hist.amount_added

    hist.month         = data.month
    hist.year          = data.year
    hist.amount_added  = data.amount_added
    hist.current_value = data.current_value
    hist.note          = data.note

    # Recalculate parent total_invested
    inv = db.query(Investment).filter(Investment.id == investment_id).first()
    if inv:
        inv.total_invested = inv.total_invested - old_amount + data.amount_added
        # Set current_value to latest history entry's value
        latest = (
            db.query(InvestmentHistory)
            .filter(InvestmentHistory.investment_id == investment_id)
            .order_by(InvestmentHistory.year.desc(), InvestmentHistory.month.desc())
            .first()
        )
        if latest:
            inv.current_value = latest.current_value

    db.commit()
    db.refresh(hist)
    return hist


@router.delete("/{investment_id}/history/{history_id}")
def delete_history(
    investment_id: int,
    history_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    hist = db.query(InvestmentHistory).filter(
        InvestmentHistory.id == history_id,
        InvestmentHistory.investment_id == investment_id,
        InvestmentHistory.user_id == current_user.id
    ).first()
    if not hist:
        raise HTTPException(status_code=404, detail="History entry not found")

    # Adjust parent total_invested
    inv = db.query(Investment).filter(Investment.id == investment_id).first()
    if inv:
        inv.total_invested -= hist.amount_added

    db.delete(hist)
    db.commit()
    return {"message": "History entry deleted"}


# ── Migration endpoint ────────────────────────────────────────────

@router.post("/migrate-from-old")
def migrate_old_entries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Migrate old-style investments (one row per month) to new design.
    Groups by name, creates one Investment record per unique name,
    adds history entries for each old row.
    """
    from datetime import date as date_type

    old_entries = (
        db.query(Investment)
        .filter(Investment.user_id == current_user.id)
        .all()
    )

    # Group by name
    by_name = {}
    for e in old_entries:
        if e.name not in by_name:
            by_name[e.name] = []
        by_name[e.name].append(e)

    migrated = 0
    for name, entries in by_name.items():
        if len(entries) <= 1:
            continue  # Already single entry, skip

        # Sort chronologically
        entries.sort(key=lambda e: (e.year, e.month))

        # Use first entry as the master
        master = entries[0]
        master.total_invested = sum(getattr(e, 'total_invested', 0) for e in entries)
        master.current_value  = entries[-1].current_value
        master.start_date     = date_type(entries[0].year, entries[0].month, 1)

        # Delete duplicate entries
        for e in entries[1:]:
            db.delete(e)

        db.commit()
        migrated += 1

    return {"message": f"Migration complete. {migrated} investments consolidated."}