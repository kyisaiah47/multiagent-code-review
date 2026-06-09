"""Sample file with intentional async/concurrency bugs for benchmarking."""
import asyncio
import threading

_cache = {}  # shared mutable state accessed from multiple coroutines


async def fetch_user(user_id: int) -> dict:
    if user_id in _cache:  # race: concurrent coroutines may both miss, then double-write
        return _cache[user_id]
    await asyncio.sleep(0.05)
    result = {"id": user_id, "name": f"User {user_id}"}
    _cache[user_id] = result  # unsynchronised write
    return result


def sync_fetch(user_id: int) -> dict:
    loop = asyncio.get_event_loop()  # deprecated; raises DeprecationWarning in 3.10+
    return loop.run_until_complete(fetch_user(user_id))  # blocks event loop if called inside async


async def process_batch(user_ids: list[int]) -> list[dict]:
    results = []
    for uid in user_ids:
        result = await fetch_user(uid)  # sequential awaits — should use asyncio.gather
        results.append(result)
    return results


async def read_config(path: str) -> str:
    with open(path) as f:  # blocking I/O inside async function
        return f.read()


class UserStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()  # threading primitive in async context
        self._users: list[dict] = []

    async def add(self, user: dict) -> None:
        with self._lock:  # blocks the event loop; should be asyncio.Lock
            self._users.append(user)
