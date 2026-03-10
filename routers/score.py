from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import extract, func

from database import get_db
from models.transaction import Transaction
from models.monthly_plan import MonthlyPlan
from models.asset import Asset
from models.liability import Liability
from models.goal import Goal
from models.budget import Budget

router = APIRouter(prefix="/score", tags=["Financial Score"])


@router.get("/current")
def get_current_score(db: Session = Depends(get_db)):
    today = date.today()
    month = today.month
    year = today.year

    # -------------------------
    # Monthly transactions
    # -------------------------
    transactions = (
        db.query(Transaction)
        .filter(extract("month", Transaction.date) == month)
        .filter(extract("year", Transaction.date) == year)
        .all()
    )

    income = sum(t.amount for t in transactions if t.type == "income")
    expenses = sum(t.amount for t in transactions if t.type == "expense")
    savings = income - expenses

    savings_rate_pct = (savings / income) * 100 if income > 0 else 0
    savings_rate_score = min(max(savings_rate_pct, 0), 100)

    # -------------------------
    # Monthly plan adherence
    # -------------------------
    monthly_plan = (
        db.query(MonthlyPlan)
        .filter(MonthlyPlan.month == month, MonthlyPlan.year == year)
        .first()
    )

    if monthly_plan:
        income_diff_pct = abs(income - monthly_plan.planned_income) / monthly_plan.planned_income * 100 if monthly_plan.planned_income > 0 else 0
        expense_diff_pct = abs(expenses - monthly_plan.planned_expense) / monthly_plan.planned_expense * 100 if monthly_plan.planned_expense > 0 else 0
        savings_diff_pct = abs(savings - monthly_plan.planned_savings) / monthly_plan.planned_savings * 100 if monthly_plan.planned_savings > 0 else 0

        avg_diff_pct = (income_diff_pct + expense_diff_pct + savings_diff_pct) / 3
        plan_adherence_score = max(0, 100 - avg_diff_pct)
    else:
        plan_adherence_score = 50

    # -------------------------
    # Budget adherence
    # -------------------------
    budgets = (
        db.query(Budget)
        .filter(Budget.month == month, Budget.year == year)
        .all()
    )

    budget_category_results = []
    total_budget = 0
    total_budget_spent = 0

    if budgets:
        category_scores = []

        for budget in budgets:
            category_expense = sum(
                t.amount
                for t in transactions
                if t.type == "expense" and t.category.lower() == budget.category.lower()
            )

            total_budget += budget.amount
            total_budget_spent += category_expense

            if budget.amount > 0:
                if category_expense <= budget.amount:
                    score = 100
                else:
                    overspend_pct = ((category_expense - budget.amount) / budget.amount) * 100
                    score = max(0, 100 - overspend_pct)
            else:
                score = 0

            category_scores.append(score)

            budget_category_results.append({
                "category": budget.category,
                "budget": round(budget.amount, 2),
                "spent": round(category_expense, 2),
                "score": round(score, 2)
            })

        budget_adherence_score = sum(category_scores) / len(category_scores) if category_scores else 50
    else:
        budget_adherence_score = 50

    # -------------------------
    # Net worth strength
    # -------------------------
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

    networth = total_assets - total_liabilities

    if total_assets > 0:
        networth_strength_score = max(0, min((networth / total_assets) * 100, 100))
    else:
        networth_strength_score = 0

    # -------------------------
    # Goal progress
    # -------------------------
    goals = db.query(Goal).all()

    if goals:
        goal_progress_values = []
        for goal in goals:
            if goal.target_amount > 0:
                goal_progress_values.append((goal.current_amount / goal.target_amount) * 100)

        goal_progress_score = min(sum(goal_progress_values) / len(goal_progress_values), 100) if goal_progress_values else 0
    else:
        goal_progress_score = 50

    # -------------------------
    # Final score
    # -------------------------
    final_score = (
        savings_rate_score * 0.25 +
        plan_adherence_score * 0.20 +
        budget_adherence_score * 0.20 +
        networth_strength_score * 0.15 +
        goal_progress_score * 0.20
    )

    final_score = round(final_score, 2)

    if final_score >= 80:
        status = "Strong"
    elif final_score >= 60:
        status = "Good"
    elif final_score >= 40:
        status = "Fair"
    else:
        status = "Poor"

    return {
        "month": month,
        "year": year,
        "score": final_score,
        "status": status,
        "components": {
            "savings_rate_score": round(savings_rate_score, 2),
            "plan_adherence_score": round(plan_adherence_score, 2),
            "budget_adherence_score": round(budget_adherence_score, 2),
            "networth_strength_score": round(networth_strength_score, 2),
            "goal_progress_score": round(goal_progress_score, 2)
        },
        "weights": {
            "savings_rate": 25,
            "plan_adherence": 20,
            "budget_adherence": 20,
            "networth_strength": 15,
            "goal_progress": 20
        },
        "budget_summary": {
            "total_budget": round(total_budget, 2),
            "total_spent": round(total_budget_spent, 2),
            "categories": budget_category_results
        },
        "explanation": {
            "savings_rate_pct": round(savings_rate_pct, 2),
            "monthly_income": round(income, 2),
            "monthly_expenses": round(expenses, 2),
            "monthly_savings": round(savings, 2),
            "networth": round(networth, 2)
        }
    }