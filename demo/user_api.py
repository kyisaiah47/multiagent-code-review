import sqlite3


def get_user(username: str):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
    return cursor.fetchone()


def get_all_orders(user_id: int):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM orders WHERE user_id = ?", (user_id,))
    order_ids = cursor.fetchall()
    orders = []
    for (oid,) in order_ids:
        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (oid,))
        orders.append({"order_id": oid, "items": cursor.fetchall()})
    return orders


def update_email(user_id: int, new_email: str) -> bool:
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, user_id))
    conn.commit()
    return cursor.rowcount > 0
