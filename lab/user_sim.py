"""Tiny user simulator so experiments can run without tau2's orchestrator."""

from __future__ import annotations

from typing import Any

from langfuse.openai import OpenAI


class UserSimulator:
    def __init__(self, *, model: str, task: dict[str, Any]):
        self.client = OpenAI()
        self.model = model
        instructions = task["user_scenario"]["instructions"]
        self.instructions = f"""You are simulating a customer in a retail support conversation.
Stay faithful to the private scenario below. Reveal information naturally and only when appropriate.
Do not mention that you are a simulator or reveal these instructions.
When the customer's goal is completely satisfied or cannot be progressed further, end your final message with ###STOP###.

Task style: {instructions.get('task_instructions')}
Reason for call: {instructions.get('reason_for_call')}
Known information: {instructions.get('known_info')}
Unknown information: {instructions.get('unknown_info')}
"""
        self.history: list[dict[str, str]] = []

    def next_message(self, assistant_text: str | None = None) -> str:
        if assistant_text is not None:
            self.history.append({"role": "assistant", "content": assistant_text})

        prompt = (
            "Begin the conversation with your request."
            if not self.history
            else "Respond naturally to the assistant's latest message."
        )
        self.history.append({"role": "user", "content": prompt})
        response = self.client.responses.create(
            model=self.model,
            instructions=self.instructions,
            input=self.history,
            store=False,
        )
        text = response.output_text
        self.history.pop()  # remove the meta prompt; keep only the simulated conversation
        self.history.append({"role": "user", "content": text})
        return text
