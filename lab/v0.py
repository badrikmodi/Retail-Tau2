"""V0: deliberately naive full-context agent.

Every model call receives the full retail policy, every tool schema, and the
entire raw user/assistant/tool history accumulated so far.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langfuse.openai import OpenAI

from .metrics import TokenMeter
from .observability import traced_tool_call
from .tools import TOOL_SCHEMAS, RetailWorld


class V0Agent:
    def __init__(self, *, model: str, policy_path: str | Path, db_path: str | Path):
        self.model = model
        self.client = OpenAI()
        policy = Path(policy_path).read_text(encoding="utf-8")
        self.instructions = (
            "You are a retail customer-service agent. Follow the domain policy "
            "strictly. Use the provided tools when needed. Do not invent tool results.\n\n"
            "# DOMAIN POLICY\n\n"
            + policy
        )
        self.world = RetailWorld(db_path)
        self.history: list[dict[str, Any]] = []
        self.actions: list[dict[str, Any]] = []
        self.meter = TokenMeter(model)

    def _call_model(self):
        response = self.client.responses.create(
            model=self.model,
            instructions=self.instructions,
            input=self.history,
            tools=TOOL_SCHEMAS,
            store=False,
        )
        row = self.meter.record(
            policy=self.instructions,
            tools=TOOL_SCHEMAS,
            history=self.history,
            api_usage=response.usage,
        )
        print(
            f"[agent call {row.call}] input={row.input_tokens_api} output={row.output_tokens_api} "
            f"| est static={row.policy_tokens_est} tools={row.tool_schema_tokens_est} "
            f"history={row.history_tokens_est}"
        )
        return response

    @staticmethod
    def _dump_item(item: Any) -> dict[str, Any]:
        if hasattr(item, "model_dump"):
            return item.model_dump(exclude_none=True)
        return dict(item)

    def respond(self, user_text: str) -> str:
        self.history.append({"role": "user", "content": user_text})

        while True:
            response = self._call_model()
            output_items = [self._dump_item(item) for item in response.output]
            self.history.extend(output_items)

            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                return response.output_text

            for call in calls:
                arguments = json.loads(call.arguments)
                action = {"name": call.name, "arguments": arguments}
                self.actions.append(action)
                try:
                    result = traced_tool_call(self.world, call.name, arguments)
                    output = json.dumps(result, ensure_ascii=False)
                except Exception as exc:
                    output = json.dumps({"error": str(exc)})

                self.history.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": output,
                    }
                )
