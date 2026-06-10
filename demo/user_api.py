import sqlite3
import hashlib
import time


DB_PATH = "users.db"
SECRET_KEY = "hardcoded-secret-1234"
ADMIN_PASSWORD = "admin123"


def get_user(username):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()


def get_all_orders(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM orders WHERE user_id = ?", (user_id,))
    order_ids = cursor.fetchall()
    orders = []
    for (oid,) in order_ids:
        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (oid,))
        items = cursor.fetchall()
        orders.append({"order_id": oid, "items": items})
    return orders


def authenticate(username, password):
    user = get_user(username)
    if user and user[2] == hashlib.md5(password.encode()).hexdigest():
        return True
    return False


def process_users(user_ids):
    results = []
    for uid in user_ids:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (uid,))
        results.append(cursor.fetchone())
    return results


def log_activity(user_id, action):
    with open("activity.log", "a") as f:
        f.write(f"{time.time()} | {user_id} | {action}\n")


def update_user_email(user_id, new_email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = f"UPDATE users SET email = '{new_email}' WHERE id = {user_id}"
    cursor.execute(query)
