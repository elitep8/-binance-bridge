from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    symbol: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    tool_calls: List[Dict[str, Any]] = []


class MarketState(BaseModel):
    symbol: str
    mark_price: Optional[float] = None
    index_price: Optional[float] = None
    funding_rate: Optional[float] = None
    open_interest: Optional[float] = None
    last_update_ms: Optional[int] = None


class PositionInfo(BaseModel):
    symbol: str
    position_amt: float
    entry_price: float
    unrealized_pnl: float
    leverage: int
    side: str


class OrderRequest(BaseModel):
    symbol: str
    side: str
    quantity: float
    order_type: str = "MARKET"
    reduce_only: bool = False
    confirm: bool = False


class OrderResponse(BaseModel):
    status: str
    raw: Dict[str, Any]
