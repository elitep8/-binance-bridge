import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from  models import ChatRequest, ChatResponse, OrderRequest, OrderResponse, PositionInfo
from  binance_client import BinanceFuturesClient
from  openai_agent import BridgeAgent

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "replace_me")
AUTO_TRADING_ENABLED = os.getenv("AUTO_TRADING_ENABLED", "false").lower() == "true"
DEFAULT_SYMBOL = os.getenv("DEFAULT_SYMBOL", "SIRENUSDT")
MAX_ORDER_NOTIONAL_USDT = float(os.getenv("MAX_ORDER_NOTIONAL_USDT", "100"))

binance = BinanceFuturesClient()
agent: BridgeAgent | None = None


async def require_token(x_bridge_token: str | None) -> None:
    if x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


async def get_market_state(symbol: str) -> Dict[str, Any]:
    symbol = symbol.upper()
    cached = binance.market_cache.get(symbol, {"symbol": symbol})
    if "mark_price" not in cached:
        premium = await binance.get_mark_price(symbol)
        oi = await binance.get_open_interest(symbol)
        cached = {
            "symbol": symbol,
            "mark_price": float(premium.get("markPrice", 0.0)),
            "index_price": float(premium.get("indexPrice", 0.0)),
            "funding_rate": float(premium.get("lastFundingRate", 0.0)),
            "open_interest": float(oi.get("openInterest", 0.0)),
            "last_update_ms": None,
        }
    else:
        try:
            oi = await binance.get_open_interest(symbol)
            cached["open_interest"] = float(oi.get("openInterest", 0.0))
        except Exception:
            cached.setdefault("open_interest", None)
    return cached


async def get_open_positions() -> List[Dict[str, Any]]:
    rows = await binance.get_positions()
    filtered: List[Dict[str, Any]] = []
    for row in rows:
        amt = float(row.get("positionAmt", 0.0))
        if amt == 0:
            continue
        filtered.append({
            "symbol": row["symbol"],
            "position_amt": amt,
            "entry_price": float(row.get("entryPrice", 0.0)),
            "unrealized_pnl": float(row.get("unRealizedProfit", 0.0)),
            "leverage": int(float(row.get("leverage", 1))),
            "side": "LONG" if amt > 0 else "SHORT",
        })
    return filtered


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    agent = BridgeAgent({
        "get_market_state": get_market_state,
        "get_open_positions": get_open_positions,
    })
    import asyncio
    asyncio.create_task(binance.market_stream_loop(DEFAULT_SYMBOL))
    if os.getenv("BINANCE_API_KEY") and os.getenv("BINANCE_API_SECRET"):
        try:
            await binance.create_listen_key()
        except Exception:
            pass
        asyncio.create_task(binance.keepalive_loop())
    yield
    await binance.session.aclose()


app = FastAPI(title="Binance OpenAI Bridge", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(str(ROOT / "static" / "index.html"))


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/market/{symbol}")
async def market(symbol: str, x_bridge_token: str | None = Header(default=None)) -> Dict[str, Any]:
    await require_token(x_bridge_token)
    return await get_market_state(symbol)


@app.get("/positions")
async def positions(x_bridge_token: str | None = Header(default=None)) -> List[PositionInfo]:
    await require_token(x_bridge_token)
    return [PositionInfo(**row) for row in await get_open_positions()]


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, x_bridge_token: str | None = Header(default=None)) -> ChatResponse:
    await require_token(x_bridge_token)
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not ready")
    result = await agent.run(payload.message, payload.symbol or DEFAULT_SYMBOL)
    return ChatResponse(**result)


@app.post("/trade/order", response_model=OrderResponse)
async def trade_order(payload: OrderRequest, x_bridge_token: str | None = Header(default=None)) -> OrderResponse:
    await require_token(x_bridge_token)
    if not AUTO_TRADING_ENABLED:
        raise HTTPException(status_code=403, detail="AUTO_TRADING_ENABLED is false")
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="confirm=true required")

    market = await get_market_state(payload.symbol)
    mark_price = float(market.get("mark_price") or 0.0)
    notional = payload.quantity * mark_price
    if notional > MAX_ORDER_NOTIONAL_USDT:
        raise HTTPException(status_code=400, detail=f"Order notional too large: {notional:.2f} > {MAX_ORDER_NOTIONAL_USDT:.2f}")

    raw = await binance.place_order(
        symbol=payload.symbol,
        side=payload.side,
        quantity=payload.quantity,
        order_type=payload.order_type,
        reduce_only=payload.reduce_only,
    )
    return OrderResponse(status="submitted", raw=raw)
