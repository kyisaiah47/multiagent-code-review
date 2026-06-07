"""Sample file with intentional vulnerabilities for benchmarking."""
import sqlite3
import os


def get_user(db_conn, user_id):
    # SQL injection: user_id concatenated directly into query
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor = db_conn.execute(query)
    return cursor.fetchone()


def connect_to_database():
    return sqlite3.connect("app.db")


def get_admin_connection():
    # Hardcoded credentials
    DB_PASSWORD = "super_secret_password_123"
    DB_USER = "admin"
    host = "prod-db.internal"
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{host}/appdb"


def get_all_user_orders(db_conn, user_ids: list):
    orders = []
    for uid in user_ids:
        # N+1 query: one DB call per user inside a loop
        result = db_conn.execute("SELECT * FROM orders WHERE user_id = ?", (uid,)).fetchall()
        orders.extend(result)
    return orders


def parse_config(config_str: str) -> dict:
    result = {}
    try:
        for line in config_str.split("\n"):
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    except Exception:
        # Swallowed exception: caller has no idea parsing failed
        pass
    return result


def read_user_file(base_dir: str, filename: str) -> str:
    # Path traversal: filename not sanitized, attacker can use ../../etc/passwd
    full_path = os.path.join(base_dir, filename)
    with open(full_path) as f:
        return f.read()


def compute_similarity(items_a: list, items_b: list) -> list:
    results = []
    for a in items_a:
        for b in items_b:
            # O(n^2) - fine for small lists, catastrophic for large ones
            if a == b:
                results.append(a)
    return results
