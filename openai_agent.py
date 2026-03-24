import os
import json
from typing import Any, Dict, List, Callable, Awaitable

from openai import AsyncOpenAI


class BridgeAgent:
    def __init__(self, tool_impls: Dict[str, Callable[..., Awaitable[Any]]]):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
        self.tool_impls = tool_impls

    async def run(self, user_message: str, symbol: str | None = None) -> Dict[str, Any]:
        tools = [
            {
                "type": "function",
                "name": "get_market_state",
                "description": "Get market state for a Binance Futures symbol.",
                "parameters": {
                    "type": "object",
                    "properties": {"symbol": {"type": "string"}},
                    "required": ["symbol"],
                },
            },
            {
                "type": "function",
                "name": "get_open_positions",
                "description": "Get current futures positions.",
                "parameters": {"type": "object", "properties": {}},
            },
        ]

        instructions = (
            "You are a crypto trading bridge assistant. "
            "Be concise, risk-aware, and never fabricate market/account state. "
            "Use tools when needed. If data is missing, say so."
        )

        input_text = user_message if not symbol else f"Symbol: {symbol}\nUser: {user_message}"
        response = await self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=input_text,
            tools=tools,
        )

        tool_calls: List[Dict[str, Any]] = []
        followup_input: List[Dict[str, Any]] = []

        for item in response.output:
            if item.type == "function_call":
                name = item.name
                args = json.loads(item.arguments or "{}")
                if name in self.tool_impls:
                    result = await self.tool_impls[name](**args)
                    tool_calls.append({"name": name, "args": args, "result": result})
                    followup_input.append({
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result),
                    })

        if followup_input:
            response = await self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=followup_input,
                previous_response_id=response.id,
            )

        return {
            "reply": getattr(response, "output_text", ""),
            "tool_calls": tool_calls,
        }
