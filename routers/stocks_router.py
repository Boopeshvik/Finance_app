import os
import base64
import httpx
from fastapi import APIRouter, Depends, HTTPException
from models.user import User
from routers.auth import get_current_user

router = APIRouter(prefix="/stocks", tags=["Stocks"])

T212_BASE = "https://live.trading212.com/api/v0"
T212_API_KEY = os.getenv("T212_API_KEY", "")
T212_API_SECRET = os.getenv("T212_API_SECRET", "")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")

# Map T212 ETF tickers to Finnhub-compatible tickers
T212_TICKER_MAP = {
    "VWRPI": "VWRL.L", "VWRPL": "VWRL.L",
    "VUAGI": "VUSA.L", "VUAGL": "VUSA.L",
    "CSNDX": "CNDX.L", "SWDA": "SWDA.L",
    "EQQQ": "EQQQ.L", "IUSA": "IUSA.L",
    "ISF": "ISF.L", "VUSA": "VUSA.L",
    "VWRL": "VWRL.L",
}


def get_t212_headers():
    if T212_API_SECRET:
        credentials = base64.b64encode(
            f"{T212_API_KEY}:{T212_API_SECRET}".encode()
        ).decode()
        return {"Authorization": f"Basic {credentials}"}
    return {"Authorization": T212_API_KEY}


def finnhub_ticker(t212_ticker: str) -> str:
    base = t212_ticker.split("_")[0].upper()
    return T212_TICKER_MAP.get(base, base)


def display_ticker(t212_ticker: str) -> str:
    return t212_ticker.split("_")[0].upper()


async def get_finnhub_data(ticker: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            metrics_resp = await client.get(
                "https://finnhub.io/api/v1/stock/metric",
                params={"symbol": ticker, "metric": "all", "token": FINNHUB_KEY}
            )
            profile_resp = await client.get(
                "https://finnhub.io/api/v1/stock/profile2",
                params={"symbol": ticker, "token": FINNHUB_KEY}
            )
            m = metrics_resp.json().get("metric", {})
            p = profile_resp.json()
            return {
                "pe_ratio": m.get("peBasicExclExtraTTM") or m.get("peNormalizedAnnual"),
                "eps": m.get("epsBasicExclExtraItemsTTM") or m.get("epsNormalizedAnnual"),
                "market_cap": p.get("marketCapitalization"),
                "revenue_ttm": m.get("revenuePerShareTTM"),
                "free_cash_flow": m.get("freeCashFlowTTM"),
                "debt_equity": m.get("totalDebt/totalEquityAnnual"),
                "dividend_yield": m.get("dividendYieldIndicatedAnnual"),
                "52w_high": m.get("52WeekHigh"),
                "52w_low": m.get("52WeekLow"),
                "beta": m.get("beta"),
                "industry": p.get("finnhubIndustry"),
                "logo": p.get("logo"),
            }
    except Exception:
        return {}


@router.get("/portfolio")
async def get_portfolio(current_user: User = Depends(get_current_user)):
    if not T212_API_KEY:
        raise HTTPException(status_code=503, detail="Trading 212 API key not configured")

    headers = get_t212_headers()

    # 1. Fetch positions
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            pos_resp = await client.get(f"{T212_BASE}/equity/portfolio", headers=headers)
            if pos_resp.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid Trading 212 API key or secret")
            if pos_resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"T212 error: {pos_resp.text}")
            positions = pos_resp.json()

            cash_resp = await client.get(f"{T212_BASE}/equity/account/cash", headers=headers)
            cash_data = cash_resp.json() if cash_resp.status_code == 200 else {}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    # 2. Fetch order history to calculate invested amounts
    # Key: lowercase ticker → {total_cost, total_qty, first_date}
    ticker_data = {}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            hist_resp = await client.get(
                f"{T212_BASE}/equity/history/orders",
                headers=headers,
                params={"limit": 200}
            )
            if hist_resp.status_code == 200:
                items = hist_resp.json().get("items", [])
                for item in items:
                    order = item.get("order", {})
                    fill = item.get("fill", {})
                    if order.get("status") != "FILLED":
                        continue

                    ticker = order.get("ticker", "").lower()  # e.g. "vwrpl_eq"
                    side = order.get("side", "BUY")
                    wallet = fill.get("walletImpact", {})
                    net_value = abs(float(wallet.get("netValue", 0)))
                    qty = abs(float(fill.get("quantity", 0)))
                    filled_at = fill.get("filledAt") or order.get("createdAt", "")

                    if ticker not in ticker_data:
                        ticker_data[ticker] = {
                            "total_cost": 0,
                            "total_qty": 0,
                            "first_date": filled_at
                        }

                    if side == "BUY":
                        ticker_data[ticker]["total_cost"] += net_value
                        ticker_data[ticker]["total_qty"] += qty
                        if filled_at and filled_at < ticker_data[ticker]["first_date"]:
                            ticker_data[ticker]["first_date"] = filled_at
                    elif side == "SELL":
                        ticker_data[ticker]["total_cost"] -= net_value
                        ticker_data[ticker]["total_qty"] -= qty
    except Exception:
        pass  # history failed, will fallback

    # 3. Enrich each position
    enriched = []
    total_invested = 0
    total_current = 0

    for pos in positions:
        t212_ticker = pos.get("ticker", "")  # e.g. "VWRPl_EQ"
        ticker_key = t212_ticker.lower()  # e.g. "vwrpl_eq"
        disp_ticker = display_ticker(t212_ticker)  # e.g. "VWRPL"
        finn_ticker = finnhub_ticker(t212_ticker)  # e.g. "VWRL.L"

        quantity = float(pos.get("quantity", 0))
        current_price = float(pos.get("currentPrice", 0))
        current_value = round(current_price * quantity, 2)

        # Get invested from history
        hist = ticker_data.get(ticker_key, {})
        total_cost = hist.get("total_cost", 0)
        first_date = hist.get("first_date", "")

        if total_cost > 0:
            invested = round(total_cost, 2)
            avg_price = round(total_cost / quantity, 4) if quantity > 0 else 0
            avg_price_source = "history"
        else:
            # Fallback to current value (no history)
            invested = current_value
            avg_price = 0
            avg_price_source = "n/a"

        pnl = round(current_value - invested, 2)
        ror = round((pnl / invested * 100), 2) if invested > 0 else 0

        # Finnhub fundamentals
        fund = await get_finnhub_data(finn_ticker)

        enriched.append({
            "ticker": t212_ticker,
            "plain_ticker": disp_ticker,
            "name": pos.get("instrument", {}).get("name", disp_ticker) if isinstance(pos.get("instrument"),
                                                                                     dict) else disp_ticker,
            "quantity": quantity,
            "avg_price": avg_price,
            "current_price": current_price,
            "invested": invested,
            "current_value": current_value,
            "pnl": pnl,
            "return_pct": ror,
            "currency": "GBP",
            "avg_price_source": avg_price_source,
            "first_invested": first_date[:10] if first_date else None,
            "pe_ratio": fund.get("pe_ratio"),
            "eps": fund.get("eps"),
            "market_cap_m": fund.get("market_cap"),
            "free_cash_flow": fund.get("free_cash_flow"),
            "debt_equity": fund.get("debt_equity"),
            "dividend_yield": fund.get("dividend_yield"),
            "52w_high": fund.get("52w_high"),
            "52w_low": fund.get("52w_low"),
            "beta": fund.get("beta"),
            "industry": fund.get("industry"),
            "logo": fund.get("logo"),
        })

        total_invested += invested
        total_current += current_value

    total_pnl = round(total_current - total_invested, 2)
    total_ror = round((total_pnl / total_invested * 100), 2) if total_invested > 0 else 0

    return {
        "summary": {
            "total_invested": round(total_invested, 2),
            "total_value": round(total_current, 2),
            "total_pnl": total_pnl,
            "total_return_pct": total_ror,
            "cash": cash_data.get("free", 0),
            "position_count": len(enriched)
        },
        "positions": enriched
    }


@router.get("/account")
async def get_account(current_user: User = Depends(get_current_user)):
    if not T212_API_KEY:
        raise HTTPException(status_code=503, detail="T212 API key not configured")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{T212_BASE}/equity/account/cash", headers=get_t212_headers())
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=resp.text)
            return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/history")
async def get_history(current_user: User = Depends(get_current_user)):
    if not T212_API_KEY:
        raise HTTPException(status_code=503, detail="T212 API key not configured")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{T212_BASE}/equity/history/orders",
                headers=get_t212_headers(),
                params={"limit": 50}
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=resp.text)
            return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/debug-history")
async def debug_history(current_user: User = Depends(get_current_user)):
    """Debug endpoint to check order history processing"""
    headers = get_t212_headers()
    ticker_data = {}
    raw_items = []
    error = None

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            hist_resp = await client.get(
                f"{T212_BASE}/equity/history/orders",
                headers=headers,
                params={"limit": 200}
            )
            status = hist_resp.status_code
            if hist_resp.status_code == 200:
                items = hist_resp.json().get("items", [])
                raw_items = [
                    {
                        "ticker": i.get("order", {}).get("ticker"),
                        "side": i.get("order", {}).get("side"),
                        "status": i.get("order", {}).get("status"),
                        "netValue": i.get("fill", {}).get("walletImpact", {}).get("netValue"),
                        "qty": i.get("fill", {}).get("quantity"),
                    }
                    for i in items
                ]
                for item in items:
                    order = item.get("order", {})
                    fill = item.get("fill", {})
                    if order.get("status") != "FILLED":
                        continue
                    ticker = order.get("ticker", "").lower()
                    side = order.get("side", "BUY")
                    wallet = fill.get("walletImpact", {})
                    net_value = abs(float(wallet.get("netValue", 0)))
                    qty = abs(float(fill.get("quantity", 0)))
                    filled_at = fill.get("filledAt") or order.get("createdAt", "")
                    if ticker not in ticker_data:
                        ticker_data[ticker] = {"total_cost": 0, "total_qty": 0, "first_date": filled_at}
                    if side == "BUY":
                        ticker_data[ticker]["total_cost"] += net_value
                        ticker_data[ticker]["total_qty"] += qty
                    elif side == "SELL":
                        ticker_data[ticker]["total_cost"] -= net_value
                        ticker_data[ticker]["total_qty"] -= qty
            else:
                error = f"HTTP {hist_resp.status_code}: {hist_resp.text}"
    except Exception as e:
        error = str(e)

    return {
        "status": status if 'status' in dir() else "unknown",
        "error": error,
        "ticker_data": ticker_data,
        "raw_items_count": len(raw_items),
        "raw_items": raw_items[:5]
    }