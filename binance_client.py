import os
import time
import hmac
import json
import hashlib
import asyncio
from typing import Any, Dict, Optional, List

import httpx
import websockets


class BinanceFuturesClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("BINANCE_API_KEY", "")
        self.api_secret = os.getenv("BINANCE_API_SECRET", "")
        self.base_url = os.getenv("BINANCE_BASE_URL", "https://fapi.binance.com")
        self.market_ws_base = "wss://fstream.binance.com/ws"
        self.session = httpx.AsyncClient(timeout=15.0)
        self.market_cache: Dict[str, Dict[str, Any]] = {}
        self.listen_key: Optional[str] = None

    def _sign(self, params: Dict[str, Any]) -> str:
        query = "&".join(f"{k}={params[k]}" for k in sorted(params.keys()))
        return hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()

    async def _signed_request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params or {}
        params["timestamp"] = int(time.time() * 1000)
        params["signature"] = self._sign(params)
        headers = {"X-MBX-APIKEY": self.api_key}
        r = await self.session.request(method, f"{self.base_url}{path}", params=params, headers=headers)
        r.raise_for_status()
        return r.json()

    async def public_request(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        r = await self.session.get(f"{self.base_url}{path}", params=params)
        r.raise_for_status()
        return r.json()

    async def get_mark_price(self, symbol: str) -> Dict[str, Any]:
        return await self.public_request("/fapi/v1/premiumIndex", {"symbol": symbol.upper()})

    async def get_open_interest(self, symbol: str) -> Dict[str, Any]:
        return await self.public_request("/fapi/v1/openInterest", {"symbol": symbol.upper()})

    async def get_positions(self) -> List[Dict[str, Any]]:
        return await self._signed_request("GET", "/fapi/v2/positionRisk")

    async def place_order(self, symbol: str, side: str, quantity: float, order_type: str = "MARKET", reduce_only: bool = False) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": quantity,
            "reduceOnly": "true" if reduce_only else "false",
        }
        return await self._signed_request("POST", "/fapi/v1/order", params)

    async def create_listen_key(self) -> str:
        headers = {"X-MBX-APIKEY": self.api_key}
        r = await self.session.post(f"{self.base_url}/fapi/v1/listenKey", headers=headers)
        r.raise_for_status()
        data = r.json()
        self.listen_key = data["listenKey"]
        return self.listen_key

    async def keepalive_listen_key(self) -> None:
        if not self.listen_key:
            return
        headers = {"X-MBX-APIKEY": self.api_key}
        r = await self.session.put(f"{self.base_url}/fapi/v1/listenKey", headers=headers)
        r.raise_for_status()

    async def keepalive_loop(self) -> None:
        while True:
            try:
                if self.listen_key:
                    await self.keepalive_listen_key()
            except Exception:
                pass
            await asyncio.sleep(50 * 60)

    async def market_stream_loop(self, symbol: str) -> None:
        stream = f"{symbol.lower()}@markPrice@1s"
        url = f"{self.market_ws_base}/{stream}"
        while True:
            try:
                async with websockets.connect(url, ping_interval=120, ping_timeout=30) as ws:
                    async for message in ws:
                        data = json.loads(message)
                        self.market_cache[symbol.upper()] = {
                            "symbol": symbol.upper(),
                            "mark_price": float(data.get("p", 0.0)),
                            "index_price": float(data.get("i", 0.0)),
                            "funding_rate": float(data.get("r", 0.0)),
                            "last_update_ms": int(data.get("E", 0)),
                        }
            except Exception:
                await asyncio.sleep(2)
