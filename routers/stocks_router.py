import os
import base64
import httpx
from fastapi import APIRouter, Depends, HTTPException
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/stocks", tags=["Stocks"])

T212_BASE       = "https://live.trading212.com/api/v0"
T212_API_KEY    = os.getenv("T212_API_KEY", "")
T212_API_SECRET = os.getenv("T212_API_SECRET", "")
FINNHUB_KEY     = os.getenv("FINNHUB_API_KEY", "")

def get_t212_headers():
    """Build Trading 212 Basic Auth headers"""
    if T212_API_SECRET:
        credentials = base64.b64encode(f"{T212_API_KEY}:{T212_API_SECRET}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}
    else:
        # Fallback to API key only (older format)
        return {"Authorization": T212_API_KEY}


def extract_ticker(t212_ticker: str) -> str:
    """Convert T212 ticker format (AAPL_US_EQ) to plain ticker (AAPL)"""
    return t212_ticker.split("_")[0]


async def get_finnhub_data(ticker: str) -> dict:
    """Fetch fundamentals from Finnhub for a given ticker"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Basic financials (P/E, EPS, Market Cap, Debt ratios)
            resp = await client.get(
                f"https://finnhub.io/api/v1/stock/metric",
                params={"symbol": ticker, "metric": "all", "token": FINNHUB_KEY}
            )
            data = resp.json()
            metrics = data.get("metric", {})

            # Company profile (Market Cap, industry, country)
            profile_resp = await client.get(
                f"https://finnhub.io/api/v1/stock/profile2",
                params={"symbol": ticker, "token": FINNHUB_KEY}
            )
            profile = profile_resp.json()

            return {
                "pe_ratio":          metrics.get("peBasicExclExtraTTM") or metrics.get("peNormalizedAnnual"),
                "eps":               metrics.get("epsBasicExclExtraItemsTTM") or metrics.get("epsNormalizedAnnual"),
                "market_cap":        profile.get("marketCapitalization"),  # in millions
                "revenue_ttm":       metrics.get("revenuePerShareTTM"),
                "free_cash_flow":    metrics.get("freeCashFlowTTM"),
                "total_debt":        metrics.get("totalDebt/totalEquityAnnual"),
                "debt_equity":       metrics.get("totalDebt/totalEquityAnnual"),
                "dividend_yield":    metrics.get("dividendYieldIndicatedAnnual"),
                "52w_high":          metrics.get("52WeekHigh"),
                "52w_low":           metrics.get("52WeekLow"),
                "beta":              metrics.get("beta"),
                "roe":               metrics.get("roeTTM"),
                "industry":          profile.get("finnhubIndustry"),
                "country":           profile.get("country"),
                "currency":          profile.get("currency"),
                "logo":              profile.get("logo"),
                "weburl":            profile.get("weburl"),
            }
    except Exception as e:
        return {"error": str(e)}


@router.get("/portfolio")
async def get_portfolio(current_user: User = Depends(get_current_user)):
    """Fetch live portfolio from Trading 212 + fundamentals from Finnhub"""
    if not T212_API_KEY:
        raise HTTPException(status_code=503, detail="Trading 212 API key not configured")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Get all positions
            pos_resp = await client.get(
                f"{T212_BASE}/equity/portfolio",
                headers=get_t212_headers()
            )
            if pos_resp.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid Trading 212 API key")
            if pos_resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Trading 212 error: {pos_resp.text}")

            positions = pos_resp.json()

            # Get account cash
            cash_resp = await client.get(
                f"{T212_BASE}/equity/account/cash",
                headers=get_t212_headers()
            )
            cash_data = cash_resp.json() if cash_resp.status_code == 200 else {}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not connect to Trading 212: {str(e)}")

    # Enrich each position with Finnhub data
    enriched = []
    total_invested = 0
    total_current  = 0

    for pos in positions:
        t212_ticker = pos.get("ticker", "")
        plain_ticker = extract_ticker(t212_ticker)

        invested = float(pos.get("averagePricePaid", 0)) * float(pos.get("quantity", 0))
        current  = float(pos.get("currentPrice", 0)) * float(pos.get("quantity", 0))
        pnl      = current - invested
        ror      = (pnl / invested * 100) if invested > 0 else 0

        # Get Finnhub fundamentals
        fundamentals = await get_finnhub_data(plain_ticker)

        enriched.append({
            "ticker":           t212_ticker,
            "plain_ticker":     plain_ticker,
            "name":             pos.get("name", plain_ticker),
            "quantity":         pos.get("quantity", 0),
            "avg_price":        pos.get("averagePricePaid", 0),
            "current_price":    pos.get("currentPrice", 0),
            "invested":         round(invested, 2),
            "current_value":    round(current, 2),
            "pnl":              round(pnl, 2),
            "return_pct":       round(ror, 2),
            "currency":         pos.get("currency", "GBP"),
            # Finnhub fundamentals
            "pe_ratio":         fundamentals.get("pe_ratio"),
            "eps":              fundamentals.get("eps"),
            "market_cap_m":     fundamentals.get("market_cap"),
            "revenue_ttm":      fundamentals.get("revenue_ttm"),
            "free_cash_flow":   fundamentals.get("free_cash_flow"),
            "debt_equity":      fundamentals.get("debt_equity"),
            "dividend_yield":   fundamentals.get("dividend_yield"),
            "52w_high":         fundamentals.get("52w_high"),
            "52w_low":          fundamentals.get("52w_low"),
            "beta":             fundamentals.get("beta"),
            "industry":         fundamentals.get("industry"),
            "logo":             fundamentals.get("logo"),
        })

        total_invested += invested
        total_current  += current

    total_pnl = total_current - total_invested
    total_ror = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    return {
        "summary": {
            "total_invested":   round(total_invested, 2),
            "total_value":      round(total_current, 2),
            "total_pnl":        round(total_pnl, 2),
            "total_return_pct": round(total_ror, 2),
            "cash":             cash_data.get("free", 0),
            "position_count":   len(enriched)
        },
        "positions": enriched
    }


@router.get("/account")
async def get_account(current_user: User = Depends(get_current_user)):
    """Get Trading 212 account summary"""
    if not T212_API_KEY:
        raise HTTPException(status_code=503, detail="Trading 212 API key not configured")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{T212_BASE}/equity/account/cash",
                headers=get_t212_headers()
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Trading 212 error: {resp.text}")
            return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/history")
async def get_history(current_user: User = Depends(get_current_user)):
    """Get Trading 212 order history"""
    if not T212_API_KEY:
        raise HTTPException(status_code=503, detail="Trading 212 API key not configured")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{T212_BASE}/equity/history/orders",
                headers=get_t212_headers(),
                params={"limit": 50}
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Trading 212 error: {resp.text}")
            return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))