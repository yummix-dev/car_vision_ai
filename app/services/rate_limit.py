"""A sliding-window counter, in memory.

This is the only thing standing between the generation endpoint and a real bill:
each call costs about $0.05 against gpt-image-2, and the endpoint is reachable
by anyone who can open the mini-app.

In memory on purpose — a restart forgiving an hour of quota is an acceptable
trade for having no dependency here. If that stops being acceptable, this is the
one module that changes.
"""

import time

_hits: dict[str, list[float]] = {}


def check(key: str, limit: int, window_seconds: int = 3600) -> bool:
    """Record a hit for `key`. Returns False when the caller is over the limit.

    A rejected call is not recorded, so being over quota never extends the
    window — the caller becomes eligible again as the earliest hits age out.
    """
    now = time.monotonic()
    hits = [t for t in _hits.get(key, []) if now - t < window_seconds]
    if len(hits) >= limit:
        _hits[key] = hits
        return False
    hits.append(now)
    _hits[key] = hits
    return True


def reset() -> None:
    _hits.clear()
