"""Plain-Python retail tools over db.json. No tau2 imports."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


def _object(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


TOOL_SCHEMAS = [
    {
        "type": "function",
        "name": "find_user_id_by_email",
        "description": "Find a retail user by email address.",
        "parameters": _object({"email": {"type": "string"}}, ["email"]),
    },
    {
        "type": "function",
        "name": "find_user_id_by_name_zip",
        "description": "Find a retail user by first name, last name, and ZIP code.",
        "parameters": _object(
            {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "zip": {"type": "string"},
            },
            ["first_name", "last_name", "zip"],
        ),
    },
    {
        "type": "function",
        "name": "get_user_details",
        "description": "Get a user, including saved payment methods and order IDs.",
        "parameters": _object({"user_id": {"type": "string"}}, ["user_id"]),
    },
    {
        "type": "function",
        "name": "get_order_details",
        "description": "Get status, items, address, fulfillment, and payments for an order.",
        "parameters": _object({"order_id": {"type": "string"}}, ["order_id"]),
    },
    {
        "type": "function",
        "name": "get_product_details",
        "description": "Get every variant, option, availability flag, and price for one product type.",
        "parameters": _object({"product_id": {"type": "string"}}, ["product_id"]),
    },
    {
        "type": "function",
        "name": "list_all_product_types",
        "description": "List every product type and its product ID in the store.",
        "parameters": _object({}, []),
    },
    {
        "type": "function",
        "name": "exchange_delivered_order_items",
        "description": "Request an exchange of delivered items for available variants of the same product types. Requires prior user confirmation according to policy.",
        "parameters": _object(
            {
                "order_id": {"type": "string"},
                "item_ids": {"type": "array", "items": {"type": "string"}},
                "new_item_ids": {"type": "array", "items": {"type": "string"}},
                "payment_method_id": {"type": "string"},
            },
            ["order_id", "item_ids", "new_item_ids", "payment_method_id"],
        ),
    },
    {
        "type": "function",
        "name": "return_delivered_order_items",
        "description": "Request a return of items from a delivered order. Requires prior user confirmation according to policy.",
        "parameters": _object(
            {
                "order_id": {"type": "string"},
                "item_ids": {"type": "array", "items": {"type": "string"}},
                "payment_method_id": {"type": "string"},
            },
            ["order_id", "item_ids", "payment_method_id"],
        ),
    },
    {
        "type": "function",
        "name": "cancel_pending_order",
        "description": "Cancel an entire pending order for an allowed reason. Requires prior user confirmation according to policy.",
        "parameters": _object(
            {
                "order_id": {"type": "string"},
                "reason": {
                    "type": "string",
                    "enum": ["no longer needed", "ordered by mistake"],
                },
            },
            ["order_id", "reason"],
        ),
    },
    {
        "type": "function",
        "name": "modify_pending_order_address",
        "description": "Change the shipping address of a pending order. Requires prior user confirmation according to policy.",
        "parameters": _object(
            {
                "order_id": {"type": "string"},
                "address1": {"type": "string"},
                "address2": {"type": "string"},
                "city": {"type": "string"},
                "state": {"type": "string"},
                "country": {"type": "string"},
                "zip": {"type": "string"},
            },
            ["order_id", "address1", "address2", "city", "state", "country", "zip"],
        ),
    },
    {
        "type": "function",
        "name": "calculate",
        "description": "Evaluate a simple arithmetic expression.",
        "parameters": _object({"expression": {"type": "string"}}, ["expression"]),
    },
]


class RetailWorld:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db = json.loads(self.db_path.read_text(encoding="utf-8"))

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self.db)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.db, indent=2), encoding="utf-8")

    def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        fn = getattr(self, name, None)
        if fn is None or name.startswith("_"):
            raise ValueError(f"Unknown tool: {name}")
        return fn(**arguments)

    def _user(self, user_id: str) -> dict[str, Any]:
        try:
            return self.db["users"][user_id]
        except KeyError as exc:
            raise ValueError("User not found") from exc

    def _order(self, order_id: str) -> dict[str, Any]:
        try:
            return self.db["orders"][order_id]
        except KeyError as exc:
            raise ValueError("Order not found") from exc

    def _product(self, product_id: str) -> dict[str, Any]:
        try:
            return self.db["products"][product_id]
        except KeyError as exc:
            raise ValueError("Product not found") from exc

    def _payment(self, user_id: str, payment_method_id: str) -> dict[str, Any]:
        user = self._user(user_id)
        try:
            return user["payment_methods"][payment_method_id]
        except KeyError as exc:
            raise ValueError("Payment method not found") from exc

    def find_user_id_by_email(self, email: str) -> str:
        for user_id, user in self.db["users"].items():
            if user["email"].lower() == email.lower():
                return user_id
        raise ValueError("User not found")

    def find_user_id_by_name_zip(self, first_name: str, last_name: str, zip: str) -> str:
        for user_id, user in self.db["users"].items():
            if (
                user["name"]["first_name"].lower() == first_name.lower()
                and user["name"]["last_name"].lower() == last_name.lower()
                and user["address"]["zip"] == zip
            ):
                return user_id
        raise ValueError("User not found")

    def get_user_details(self, user_id: str) -> dict[str, Any]:
        return copy.deepcopy(self._user(user_id))

    def get_order_details(self, order_id: str) -> dict[str, Any]:
        return copy.deepcopy(self._order(order_id))

    def get_product_details(self, product_id: str) -> dict[str, Any]:
        return copy.deepcopy(self._product(product_id))

    def list_all_product_types(self) -> dict[str, str]:
        return dict(sorted((p["name"], p["product_id"]) for p in self.db["products"].values()))

    def _variant(self, product_id: str, item_id: str) -> dict[str, Any]:
        product = self._product(product_id)
        try:
            return product["variants"][item_id]
        except KeyError as exc:
            raise ValueError(f"Variant {item_id} not found for product {product_id}") from exc

    def exchange_delivered_order_items(
        self,
        order_id: str,
        item_ids: list[str],
        new_item_ids: list[str],
        payment_method_id: str,
    ) -> dict[str, Any]:
        order = self._order(order_id)
        if order["status"] != "delivered":
            raise ValueError("Non-delivered order cannot be exchanged")
        if len(item_ids) != len(new_item_ids):
            raise ValueError("Old/new item counts must match")
        self._payment(order["user_id"], payment_method_id)

        diff = 0.0
        for old_id, new_id in zip(item_ids, new_item_ids):
            old = next((x for x in order["items"] if x["item_id"] == old_id), None)
            if old is None:
                raise ValueError(f"Item {old_id} not found in order")
            new = self._variant(old["product_id"], new_id)
            if not new["available"]:
                raise ValueError(f"New item {new_id} is unavailable")
            diff += new["price"] - old["price"]

        order["status"] = "exchange requested"
        order["exchange_items"] = sorted(item_ids)
        order["exchange_new_items"] = sorted(new_item_ids)
        order["exchange_payment_method_id"] = payment_method_id
        order["exchange_price_difference"] = round(diff, 2)
        return copy.deepcopy(order)

    def return_delivered_order_items(
        self, order_id: str, item_ids: list[str], payment_method_id: str
    ) -> dict[str, Any]:
        order = self._order(order_id)
        if order["status"] != "delivered":
            raise ValueError("Non-delivered order cannot be returned")
        existing = [item["item_id"] for item in order["items"]]
        for item_id in item_ids:
            if item_id not in existing:
                raise ValueError(f"Item {item_id} not found in order")
        self._payment(order["user_id"], payment_method_id)
        order["status"] = "return requested"
        order["return_items"] = sorted(item_ids)
        order["return_payment_method_id"] = payment_method_id
        return copy.deepcopy(order)

    def cancel_pending_order(self, order_id: str, reason: str) -> dict[str, Any]:
        order = self._order(order_id)
        if order["status"] != "pending":
            raise ValueError("Non-pending order cannot be cancelled")
        if reason not in {"no longer needed", "ordered by mistake"}:
            raise ValueError("Invalid cancellation reason")

        refunds = []
        for payment in list(order.get("payment_history", [])):
            if payment["transaction_type"] != "payment":
                continue
            refunds.append(
                {
                    "transaction_type": "refund",
                    "amount": payment["amount"],
                    "payment_method_id": payment["payment_method_id"],
                }
            )
            method = self._payment(order["user_id"], payment["payment_method_id"])
            if method.get("source") == "gift_card":
                method["balance"] = round(method.get("balance", 0) + payment["amount"], 2)

        order["status"] = "cancelled"
        order["cancel_reason"] = reason
        order.setdefault("payment_history", []).extend(refunds)
        return copy.deepcopy(order)

    def modify_pending_order_address(
        self,
        order_id: str,
        address1: str,
        address2: str,
        city: str,
        state: str,
        country: str,
        zip: str,
    ) -> dict[str, Any]:
        order = self._order(order_id)
        if "pending" not in order["status"]:
            raise ValueError("Non-pending order cannot be modified")
        order["address"] = {
            "address1": address1,
            "address2": address2,
            "city": city,
            "state": state,
            "country": country,
            "zip": zip,
        }
        return copy.deepcopy(order)

    def calculate(self, expression: str) -> str:
        if not all(c in "0123456789+-*/(). " for c in expression):
            raise ValueError("Invalid characters in expression")
        return str(round(float(eval(expression, {"__builtins__": None}, {})), 2))
