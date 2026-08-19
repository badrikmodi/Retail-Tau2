"""Langfuse-only tracing helpers.

This module observes the lab; it does not own agent state, routing, prompts,
or control flow. The rest of the codebase can ignore it conceptually.
"""

from __future__ import annotations

from typing import Any

from langfuse import get_client, observe


# One root trace per CLI experiment. Input/output capture is disabled here because
# the actual LLM inputs/outputs are already captured by the Langfuse OpenAI wrapper.
trace_experiment = observe(
    name="retail-token-efficiency-experiment",
    as_type="agent",
    capture_input=False,
    capture_output=False,
)


def traced_tool_call(world: Any, name: str, arguments: dict[str, Any]) -> Any:
    """Execute one of our Python tools while exposing it as a Langfuse tool span."""
    langfuse = get_client()
    with langfuse.start_as_current_observation(
        as_type="tool",
        name=name,
        input=arguments,
    ) as span:
        try:
            result = world.execute(name, arguments)
        except Exception as exc:
            span.update(
                level="ERROR",
                status_message=str(exc),
                output={"error": str(exc)},
            )
            raise

        span.update(output=result)
        return result


def flush_traces() -> None:
    """Flush buffered traces before the short-lived CLI process exits."""
    get_client().flush()
