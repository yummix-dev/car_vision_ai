"""Orders — the durable record a payment reconciles against.

The shop deliberately kept no order store before payments existed; see
migration 009. Only the transaction lives here (code, amount, method, status),
never the customer's name or phone — those stay in the manager's chat.
"""

import time

from app.db import connect

METHODS = ("cash", "telegram", "uzum")
STATUSES = ("manual", "pending", "paid", "failed")


def create(
    *,
    order_code: str,
    telegram_id: int | None,
    car_label: str,
    positions: int,
    total: int,
    payment_method: str,
    payment_status: str,
) -> dict:
    if payment_method not in METHODS:
        raise ValueError(f"unknown payment method: {payment_method}")
    if payment_status not in STATUSES:
        raise ValueError(f"unknown payment status: {payment_status}")
    now = int(time.time())
    with connect(immediate=True) as conn:
        conn.execute(
            "INSERT INTO orders(order_code, telegram_id, car_label, positions, total,"
            " payment_method, payment_status, created_at, updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (order_code, telegram_id, car_label, positions, total,
             payment_method, payment_status, now, now),
        )
        return dict(conn.execute(
            "SELECT * FROM orders WHERE order_code=?", (order_code,)
        ).fetchone())


def get_by_code(order_code: str) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE order_code=?", (order_code,)
        ).fetchone()
    return dict(row) if row else None


def set_status(order_code: str, status: str, provider_ref: str | None = None) -> None:
    """Move an order's payment status. `provider_ref` is set once, when the
    provider first hands back an invoice/installment id."""
    if status not in STATUSES:
        raise ValueError(f"unknown payment status: {status}")
    with connect(immediate=True) as conn:
        if provider_ref is not None:
            conn.execute(
                "UPDATE orders SET payment_status=?, provider_ref=?, updated_at=?"
                " WHERE order_code=?",
                (status, provider_ref, int(time.time()), order_code),
            )
        else:
            conn.execute(
                "UPDATE orders SET payment_status=?, updated_at=? WHERE order_code=?",
                (status, int(time.time()), order_code),
            )
