import os
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import extract
from datetime import datetime

import anthropic

from database import get_db
from models.transaction import Transaction
from models.budget import Budget
from models.goal import Goal
from routers.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/ai", tags=["AI"])

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ── Schema for natural language transaction parsing ──────────────
class NLTransactionRequest(BaseModel):
    text: str


# ═══════════════════════════════════════════════════════════════
#  FEATURE 1 — AI Financial Insights
# ═══════════════════════════════════════════════════════════════

@router.get("/insights")
def get_ai_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyses the current user's transactions, budgets and goals
    and returns personalised AI-generated financial insights.
    """
    now = datetime.now()
    current_month = now.month
    current_year = now.year

    # Fetch last 3 months of transactions
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == current_user.id)
        .order_by(Transaction.date.desc())
        .limit(100)
        .all()
    )

    # Fetch current month budgets
    budgets = (
        db.query(Budget)
        .filter(
            Budget.user_id == current_user.id,
            Budget.month == current_month,
            Budget.year == current_year
        )
        .all()
    )

    # Fetch active goals
    goals = (
        db.query(Goal)
        .filter(Goal.user_id == current_user.id)
        .all()
    )

    # Build summary data for the prompt
    tx_summary = [
        {
            "date": str(t.date),
            "type": t.type,
            "category": t.category,
            "amount": float(t.amount),
            "description": t.description or ""
        }
        for t in transactions
    ]

    budget_summary = [
        {
            "category": b.category,
            "amount": float(b.amount),
            "month": b.month,
            "year": b.year
        }
        for b in budgets
    ]

    goal_summary = [
        {
            "name": g.name,
            "target_amount": float(g.target_amount),
            "current_amount": float(g.current_amount),
            "target_date": str(g.target_date)
        }
        for g in goals
    ]

    # Calculate spending by category this month
    monthly_spending = {}
    monthly_income = 0
    for t in transactions:
        if hasattr(t.date, 'month'):
            tx_month = t.date.month
            tx_year = t.date.year
        else:
            parts = str(t.date).split("-")
            tx_month = int(parts[1])
            tx_year = int(parts[0])

        if tx_month == current_month and tx_year == current_year:
            if t.type == "expense":
                monthly_spending[t.category] = monthly_spending.get(t.category, 0) + float(t.amount)
            elif t.type == "income":
                monthly_income += float(t.amount)

    prompt = f"""You are a friendly and insightful personal finance advisor.
Analyse this user's financial data and provide exactly 4 specific, actionable insights.

Current month: {now.strftime('%B %Y')}
Monthly income this month: £{monthly_income:.2f}
Spending by category this month: {json.dumps(monthly_spending, indent=2)}
Monthly budgets: {json.dumps(budget_summary, indent=2)}
Financial goals: {json.dumps(goal_summary, indent=2)}
Recent transactions (last 100): {json.dumps(tx_summary, indent=2)}

Provide exactly 4 insights in this JSON format:
{{
  "insights": [
    {{
      "title": "Short title (5 words max)",
      "message": "Specific insight with actual numbers from their data (2-3 sentences)",
      "type": "positive|warning|tip|info"
    }}
  ],
  "summary": "One sentence overall financial health summary"
}}

Rules:
- Use actual numbers from their data (£ amounts, percentages)
- Be specific not generic
- type must be one of: positive, warning, tip, info
- If no data available, give general saving tips
- Always respond with valid JSON only, no extra text"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = message.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)
        return result

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI returned invalid response. Please try again.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


# ═══════════════════════════════════════════════════════════════
#  FEATURE 2 — Natural Language Transaction Parser
# ═══════════════════════════════════════════════════════════════

@router.post("/parse-transaction")
def parse_transaction(
    request: NLTransactionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Takes a natural language string like 'spent £45 on groceries yesterday'
    and returns a structured transaction object ready to save.
    """
    today = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""Extract transaction details from this text and return JSON only.

Text: "{request.text}"
Today's date: {today}

Return this exact JSON structure:
{{
  "type": "income or expense",
  "category": "best matching category name",
  "amount": 0.00,
  "date": "YYYY-MM-DD",
  "description": "brief description"
}}

Rules:
- type must be "income" or "expense"
- amount must be a positive number
- date must be YYYY-MM-DD format
- if date is "yesterday" calculate from today ({today})
- if no date mentioned use today ({today})
- category should be one of: Food, Transport, Entertainment, Shopping, Health, Housing, Utilities, Salary, Freelance, Other
- Return valid JSON only, no extra text"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = message.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)

        # Validate required fields
        required = ["type", "category", "amount", "date", "description"]
        for field in required:
            if field not in result:
                raise HTTPException(status_code=422, detail=f"AI could not parse '{field}' from your text")

        return result

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI could not understand that. Try: 'spent £45 on groceries yesterday'")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")