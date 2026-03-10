from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import extract, func

from database import get_db
from models.transaction import Transaction
from models.monthly_plan import MonthlyPlan
from models.yearly_plan import YearlyPlan
from models.asset import Asset
from models.liability import Liability
from models.goal import Goal
from models.budget import Budget

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview")
def get_dashboard_overview(db: Session = Depends(get_db)):
    today = date.today()
    month = today.month
    year = today.year

    # -------------------------
    # Monthly summary
    # -------------------------
    monthly_transactions = (
        db.query(Transaction)
        .filter(extract("month", Transaction.date) == month)
        .filter(extract("year", Transaction.date) == year)
        .all()
    )

    monthly_income = sum(t.amount for t in monthly_transactions if t.type == "income")
    monthly_expenses = sum(t.amount for t in monthly_transactions if t.type == "expense")
    monthly_savings = monthly_income - monthly_expenses
    monthly_savings_rate = (monthly_savings / monthly_income * 100) if monthly_income > 0 else 0

    # -------------------------
    # Monthly plan vs actual
    # -------------------------
    monthly_plan = (
        db.query(MonthlyPlan)
        .filter(MonthlyPlan.month == month, MonthlyPlan.year == year)
        .first()
    )

    if monthly_plan:
        monthly_plan_data = {
            "planned": {
                "income": round(monthly_plan.planned_income, 2),
                "expense": round(monthly_plan.planned_expense, 2),
                "savings": round(monthly_plan.planned_savings, 2)
            },
            "actual": {
                "income": round(monthly_income, 2),
                "expense": round(monthly_expenses, 2),
                "savings": round(monthly_savings, 2)
            },
            "difference": {
                "income": round(monthly_income - monthly_plan.planned_income, 2),
                "expense": round(monthly_expenses - monthly_plan.planned_expense, 2),
                "savings": round(monthly_savings - monthly_plan.planned_savings, 2)
            }
        }
    else:
        monthly_plan_data = None

    # -------------------------
    # Yearly plan vs actual + forecast
    # -------------------------
    yearly_plan = db.query(YearlyPlan).filter(YearlyPlan.year == year).first()

    yearly_transactions = (
        db.query(Transaction)
        .filter(extract("year", Transaction.date) == year)
        .all()
    )

    yearly_income_so_far = sum(t.amount for t in yearly_transactions if t.type == "income")
    yearly_expenses_so_far = sum(t.amount for t in yearly_transactions if t.type == "expense")
    yearly_savings_so_far = yearly_income_so_far - yearly_expenses_so_far

    months_passed = today.month

    forecast_income = (yearly_income_so_far / months_passed) * 12 if months_passed > 0 else 0
    forecast_expense = (yearly_expenses_so_far / months_passed) * 12 if months_passed > 0 else 0
    forecast_savings = (yearly_savings_so_far / months_passed) * 12 if months_passed > 0 else 0

    if yearly_plan:
        yearly_plan_data = {
            "planned": {
                "income": round(yearly_plan.planned_income, 2),
                "expense": round(yearly_plan.planned_expense, 2),
                "savings": round(yearly_plan.planned_savings, 2)
            },
            "so_far": {
                "income": round(yearly_income_so_far, 2),
                "expense": round(yearly_expenses_so_far, 2),
                "savings": round(yearly_savings_so_far, 2)
            },
            "forecast": {
                "income": round(forecast_income, 2),
                "expense": round(forecast_expense, 2),
                "savings": round(forecast_savings, 2)
            },
            "difference_vs_plan": {
                "income": round(forecast_income - yearly_plan.planned_income, 2),
                "expense": round(forecast_expense - yearly_plan.planned_expense, 2),
                "savings": round(forecast_savings - yearly_plan.planned_savings, 2)
            }
        }
    else:
        yearly_plan_data = None

    # -------------------------
    # Budget summary
    # -------------------------
    budgets = (
        db.query(Budget)
        .filter(Budget.month == month, Budget.year == year)
        .order_by(Budget.category.asc())
        .all()
    )

    budget_items = []
    total_budget = 0
    total_budget_spent = 0

    for budget in budgets:
        category_spent = sum(
            t.amount
            for t in monthly_transactions
            if t.type == "expense" and t.category.lower() == budget.category.lower()
        )

        remaining = budget.amount - category_spent
        over_budget = max(0, category_spent - budget.amount)
        usage_percentage = (category_spent / budget.amount * 100) if budget.amount > 0 else 0

        if category_spent < budget.amount:
            status = "within_budget"
        elif category_spent == budget.amount:
            status = "on_budget"
        else:
            status = "over_budget"

        budget_items.append({
            "category": budget.category,
            "budget": round(budget.amount, 2),
            "actual_spent": round(category_spent, 2),
            "remaining": round(max(0, remaining), 2),
            "over_budget": round(over_budget, 2),
            "usage_percentage": round(usage_percentage, 2),
            "status": status
        })

        total_budget += budget.amount
        total_budget_spent += category_spent

    budget_summary = {
        "total_budget": round(total_budget, 2),
        "total_spent": round(total_budget_spent, 2),
        "total_remaining": round(max(0, total_budget - total_budget_spent), 2),
        "items": budget_items
    }

    # -------------------------
    # Current net worth
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

    # -------------------------
    # Goals summary
    # -------------------------
    goals = db.query(Goal).order_by(Goal.target_date.asc(), Goal.id.asc()).all()

    goals_summary = []
    goal_progress_values = []

    for goal in goals:
        progress_percentage = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
        remaining_amount = goal.target_amount - goal.current_amount

        goals_summary.append({
            "id": goal.id,
            "name": goal.name,
            "target_amount": round(goal.target_amount, 2),
            "current_amount": round(goal.current_amount, 2),
            "target_date": goal.target_date,
            "progress_percentage": round(progress_percentage, 2),
            "remaining_amount": round(remaining_amount, 2)
        })

        goal_progress_values.append(progress_percentage)

    avg_goal_progress = sum(goal_progress_values) / len(goal_progress_values) if goal_progress_values else 0

    # -------------------------
    # Financial score with budget adherence
    # -------------------------
    savings_rate_score = min(max(monthly_savings_rate, 0), 100)

    if monthly_plan:
        income_diff_pct = abs(monthly_income - monthly_plan.planned_income) / monthly_plan.planned_income * 100 if monthly_plan.planned_income > 0 else 0
        expense_diff_pct = abs(monthly_expenses - monthly_plan.planned_expense) / monthly_plan.planned_expense * 100 if monthly_plan.planned_expense > 0 else 0
        savings_diff_pct = abs(monthly_savings - monthly_plan.planned_savings) / monthly_plan.planned_savings * 100 if monthly_plan.planned_savings > 0 else 0

        avg_diff_pct = (income_diff_pct + expense_diff_pct + savings_diff_pct) / 3
        plan_adherence_score = max(0, 100 - avg_diff_pct)
    else:
        plan_adherence_score = 50

    if budgets:
        category_scores = []

        for budget in budgets:
            category_spent = sum(
                t.amount
                for t in monthly_transactions
                if t.type == "expense" and t.category.lower() == budget.category.lower()
            )

            if budget.amount > 0:
                if category_spent <= budget.amount:
                    score = 100
                else:
                    overspend_pct = ((category_spent - budget.amount) / budget.amount) * 100
                    score = max(0, 100 - overspend_pct)
            else:
                score = 0

            category_scores.append(score)

        budget_adherence_score = sum(category_scores) / len(category_scores) if category_scores else 50
    else:
        budget_adherence_score = 50

    networth_strength_score = (networth / total_assets * 100) if total_assets > 0 else 0
    networth_strength_score = max(0, min(networth_strength_score, 100))

    goal_progress_score = min(avg_goal_progress, 100) if goals else 50

    final_score = (
        savings_rate_score * 0.25 +
        plan_adherence_score * 0.20 +
        budget_adherence_score * 0.20 +
        networth_strength_score * 0.15 +
        goal_progress_score * 0.20
    )

    final_score = round(final_score, 2)

    if final_score >= 80:
        score_status = "Strong"
    elif final_score >= 60:
        score_status = "Good"
    elif final_score >= 40:
        score_status = "Fair"
    else:
        score_status = "Poor"

    return {
        "period": {
            "month": month,
            "year": year
        },
        "monthly_summary": {
            "income": round(monthly_income, 2),
            "expenses": round(monthly_expenses, 2),
            "savings": round(monthly_savings, 2),
            "savings_rate": round(monthly_savings_rate, 2),
            "transaction_count": len(monthly_transactions)
        },
        "monthly_plan": monthly_plan_data,
        "budget_summary": budget_summary,
        "yearly_plan": yearly_plan_data,
        "networth": {
            "asset_snapshot_date": latest_asset_date,
            "liability_snapshot_date": latest_liability_date,
            "total_assets": round(total_assets, 2),
            "total_liabilities": round(total_liabilities, 2),
            "networth": round(networth, 2)
        },
        "goals": {
            "count": len(goals_summary),
            "average_progress_percentage": round(avg_goal_progress, 2),
            "items": goals_summary
        },
        "financial_score": {
            "score": final_score,
            "status": score_status,
            "components": {
                "savings_rate_score": round(savings_rate_score, 2),
                "plan_adherence_score": round(plan_adherence_score, 2),
                "budget_adherence_score": round(budget_adherence_score, 2),
                "networth_strength_score": round(networth_strength_score, 2),
                "goal_progress_score": round(goal_progress_score, 2)
            }
        }
    }