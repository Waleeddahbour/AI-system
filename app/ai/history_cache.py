import time


class HistoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, list[dict[str, str]]]] = {}

    def get(self, key: str) -> list[dict[str, str]] | None:
        item = self._store.get(key)
        if item is None:
            return None

        expires_at, value = item
        if time.time() > expires_at:
            del self._store[key]
            return None

        return value

    def set(self, key: str, value: list[dict[str, str]], ttl: int = 300) -> None:
        self._store[key] = (time.time() + ttl, value)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


history_cache = HistoryCache()
