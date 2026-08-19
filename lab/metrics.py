"""Token/context measurements kept separate from agent behavior."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

import tiktoken


@dataclass
class CallMetrics:
    call: int
    policy_tokens_est: int
    tool_schema_tokens_est: int
    history_tokens_est: int
    input_tokens_api: int | None
    output_tokens_api: int | None


class TokenMeter:
    def __init__(self, model: str):
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("o200k_base")
        self.rows: list[CallMetrics] = []

    def count_text(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def count_json(self, value: Any) -> int:
        return self.count_text(json.dumps(value, ensure_ascii=False, sort_keys=True))

    def record(
        self,
        *,
        policy: str,
        tools: list[dict[str, Any]],
        history: list[dict[str, Any]],
        api_usage: Any = None,
    ) -> CallMetrics:
        row = CallMetrics(
            call=len(self.rows) + 1,
            policy_tokens_est=self.count_text(policy),
            tool_schema_tokens_est=self.count_json(tools),
            history_tokens_est=self.count_json(history),
            input_tokens_api=getattr(api_usage, "input_tokens", None),
            output_tokens_api=getattr(api_usage, "output_tokens", None),
        )
        self.rows.append(row)
        return row

    def summary(self) -> dict[str, Any]:
        return {
            "calls": [asdict(row) for row in self.rows],
            "cumulative_input_tokens_api": sum(
                row.input_tokens_api or 0 for row in self.rows
            ),
            "cumulative_output_tokens_api": sum(
                row.output_tokens_api or 0 for row in self.rows
            ),
        }
