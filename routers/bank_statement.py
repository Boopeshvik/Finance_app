import os
import json
import base64
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

import anthropic

from database import get_db
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/ai/bank", tags=["Bank Statement"])

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── Category rules tuned to real Lloyds UK transactions ──────────────────────
CATEGORY_RULES = [
    (["lettings", "letting", "rent", "estate agent", "mortgage", "property", "anthony lettings"], "Housing"),
    (["mars petcare uk", "mars petcare", "mars nederland", "petcare uk"], "Salary"),
    (["octopus energy", "british gas", "eon ", "bulb", "thames water",
      "vodafone", "lebara", "o2 ", "three", "ee ", "bt ", "sky ",
      "virgin media", "stevenage bc", "council tax", "herts county",
      "emac", "post office life", "water ", "electric", "energy"], "Utilities"),
    (["tfl", "lexus fin", "shell", "bp ", "esso", "national rail",
      "trainline", "parking", "uber", "taxi", "bus ", "petrol", "mot "], "Transport"),
    (["tesco", "sainsbury", "asda", "morrisons", "waitrose", "aldi", "lidl",
      "co-op", "iceland", "greggs", "mcdonalds", "kfc", "subway", "costa",
      "starbucks", "pret", "deliveroo", "uber eats", "just eat",
      "star groceries", "vaidehi", "old town food", "eurest", "grocery", "food"], "Food"),
    (["netflix", "spotify", "amazon prime", "disney", "apple.com", "apple ",
      "google play", "steam", "playstation", "cinema", "vue", "odeon",
      "cineworld", "youtube", "prime video"], "Entertainment"),
    (["amazon", "ebay", "argos", "currys", "john lewis", "next ",
      "primark", "h&m", "zara", "asos", "boots", "superdrug", "ikea"], "Shopping"),
    (["everyone active", "pure gym", "david lloyd", "nuffield", "gym",
      "pharmacy", "nhs", "dentist", "chemist", "wellhub", "fitness"], "Health"),
    (["vanguard", "hargreaves", "isa ", "fidelity", "nutmeg", "investment"], "Savings"),
    (["insurance", "aviva", "admiral", "axa", "direct line",
      "post office life", "life assurance"], "Insurance"),
]

INCOME_TYPES  = {"BGC", "FPI", "MPI", "DEP", "COR"}
EXPENSE_TYPES = {"DEB", "DD", "SO", "FPO", "MPO", "BP", "CHQ", "FEE", "CHG", "CPT", "PAY"}


def guess_category(description: str, type_code: str, is_income: bool) -> str:
    desc = description.lower()

    if type_code == "SO" and any(k in desc for k in ["lettings", "rent", "anthony"]):
        return "Housing"
    if type_code in ("BGC", "FPI") and "mars" in desc:
        return "Salary"
    if type_code == "DD" and "vanguard" in desc:
        return "Savings"
    if type_code == "FPO" and any(k in desc for k in ["american exp", "lloyds bank platin", "credit card"]):
        return "Other"
    if is_income and type_code in ("FPI", "BGC"):
        if any(k in desc for k in ["salary", "wages", "payroll", "mars", "petcare"]):
            return "Salary"
        return "Other"

    for keywords, category in CATEGORY_RULES:
        if any(k in desc for k in keywords):
            return category

    return "Other"


@router.post("/parse-statement")
async def parse_bank_statement(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Please upload a PDF file")

    try:
        pdf_bytes = await file.read()
        if len(pdf_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")
        pdf_base64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {str(e)}")

    prompt = """This is a Lloyds Bank Classic account statement PDF.

Columns: Date | Description | Type | Money In (£) | Money Out (£) | Balance (£)

Date format in PDF: "DD Mon YY" e.g. "02 Mar 26" = 2 March 2026

Transaction type codes:
BGC=Bank Giro Credit, BP=Bill Payment, CHG=Charge, CHQ=Cheque
COR=Correction, CPT=Cashpoint, DD=Direct Debit, DEB=Debit Card
DEP=Deposit, FEE=Fixed Service, FPI=Faster Payment In, FPO=Faster Payment Out
MPI=Mobile Payment In, MPO=Mobile Payment Out, PAY=Payment
SO=Standing Order, TFR=Transfer

Extract EVERY transaction. Ignore Balance column, page headers, page footers, and the "Transaction types" legend at the end.

Return ONLY this JSON (no markdown fences, no extra text):
{
  "statement_period": "01 March 2026 to 27 March 2026",
  "account_holder": "full name",
  "sort_code": "30-96-64",
  "account_number": "87406268",
  "total_money_in": 6749.42,
  "total_money_out": 8046.27,
  "transactions": [
    {
      "date": "2026-03-02",
      "description": "exact description from statement",
      "type_code": "DEB",
      "money_in": 0,
      "money_out": 16.99
    }
  ]
}

Rules:
- Convert "DD Mon YY" to YYYY-MM-DD (02 Mar 26 → 2026-03-02)
- money_in and money_out are numbers, use 0 when blank
- Include ALL transactions, none skipped
- Return ONLY valid JSON"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        raw = message.content[0].text.strip()

        # Strip markdown fences if present
        if "```" in raw:
            for part in raw.split("```"):
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    raw = part
                    break

        result = json.loads(raw)
        transactions = result.get("transactions", [])

        enriched = []
        for tx in transactions:
            money_in  = float(tx.get("money_in",  0) or 0)
            money_out = float(tx.get("money_out", 0) or 0)
            is_income = money_in > 0 and money_out == 0
            type_code = tx.get("type_code", "").upper().strip()

            if is_income or type_code in INCOME_TYPES:
                tx_type = "income"
                amount  = money_in
            else:
                tx_type = "expense"
                amount  = money_out

            category = guess_category(tx.get("description", ""), type_code, is_income)

            enriched.append({
                "date":               tx.get("date", ""),
                "description":        tx.get("description", ""),
                "type_code":          type_code,
                "type":               tx_type,
                "amount":             round(amount, 2),
                "suggested_category": category
            })

        return {
            "success":           True,
            "statement_period":  result.get("statement_period", ""),
            "account_holder":    result.get("account_holder", ""),
            "sort_code":         result.get("sort_code", ""),
            "account_number":    result.get("account_number", ""),
            "total_money_in":    result.get("total_money_in",  0),
            "total_money_out":   result.get("total_money_out", 0),
            "transaction_count": len(enriched),
            "transactions":      enriched
        }

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Could not parse AI response: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing statement: {str(e)}")