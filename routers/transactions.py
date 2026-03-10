from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract

from database import get_db
from models.transaction import Transaction
from models.category import Category
from models.user import User
from routers.auth import get_current_user
from schemas.transaction_schema import TransactionCreate, TransactionResponse

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("/", response_model=TransactionResponse)
def create_transaction(
    data: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    transaction_type = data.type.strip().lower()
    category_name = data.category.strip().lower()

    if transaction_type not in ["income", "expense"]:
        raise HTTPException(status_code=400, detail="type must be either 'income' or 'expense'")

    category = (
        db.query(Category)
        .filter(Category.name == category_name, Category.user_id == current_user.id)
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=400,
            detail=f"Category '{category_name}' does not exist. Please create it first."
        )

    if category.type != transaction_type:
        raise HTTPException(
            status_code=400,
            detail=f"Category '{category_name}' is of type '{category.type}' and cannot be used for '{transaction_type}'."
        )

    transaction = Transaction(
        type=transaction_type,
        category=category_name,
        amount=data.amount,
        date=data.date,
        description=data.description,
        user_id=current_user.id
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/", response_model=list[TransactionResponse])
def get_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(Transaction)
        .filter(Transaction.user_id == current_user.id)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .all()
    )


@router.get("/monthly-summary")
def get_monthly_summary(
    month: int,
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == current_user.id)
        .filter(extract("month", Transaction.date) == month)
        .filter(extract("year", Transaction.date) == year)
        .all()
    )

    income = sum(t.amount for t in transactions if t.type == "income")
    expenses = sum(t.amount for t in transactions if t.type == "expense")
    savings = income - expenses
    savings_rate = (savings / income * 100) if income > 0 else 0

    return {
        "month": month,
        "year": year,
        "income": round(income, 2),
        "expenses": round(expenses, 2),
        "savings": round(savings, 2),
        "savings_rate": round(savings_rate, 2),
        "transaction_count": len(transactions)
    }


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    data: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
        .first()
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    transaction_type = data.type.strip().lower()
    category_name = data.category.strip().lower()

    if transaction_type not in ["income", "expense"]:
        raise HTTPException(status_code=400, detail="type must be either 'income' or 'expense'")

    category = (
        db.query(Category)
        .filter(Category.name == category_name, Category.user_id == current_user.id)
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=400,
            detail=f"Category '{category_name}' does not exist. Please create it first."
        )

    if category.type != transaction_type:
        raise HTTPException(
            status_code=400,
            detail=f"Category '{category_name}' is of type '{category.type}' and cannot be used for '{transaction_type}'."
        )

    transaction.type = transaction_type
    transaction.category = category_name
    transaction.amount = data.amount
    transaction.date = data.date
    transaction.description = data.description

    db.commit()
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
        .first()
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(transaction)
    db.commit()

    return {"message": "Transaction deleted successfully"}