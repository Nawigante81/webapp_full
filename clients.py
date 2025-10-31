import random
import time
import httpx
from typing import Any, Dict, Optional

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118 Safari/537.36",
]


def get_client() -> httpx.Client:
    return httpx.Client(
        http2=False,
        timeout=20.0,
        follow_redirects=True,
        headers={
            "User-Agent": random.choice(UAS),
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8",
            "Accept": "application/json, text/plain, */*",
        },
    )


def fetch(
    c: httpx.Client,
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    tries: int = 5,
    base: float = 1.2,
) -> Any:
    """GET JSON with retry and jittered backoff."""
    for i in range(1, tries + 1):
        try:
            r = c.get(url, params=params, headers=headers)
            r.raise_for_status()
            # gentle throttle
            time.sleep(0.4 + random.random() * 0.6)
            return r.json()
        except httpx.HTTPStatusError as e:
            # Don't retry on 401 Unauthorized - it won't succeed
            if e.response.status_code == 401:
                raise
            # Handle rate limiting: respect Retry-After when 429
            if e.response.status_code == 429:
                ra = e.response.headers.get("Retry-After")
                try:
                    wait = float(ra)
                except (TypeError, ValueError):
                    wait = base * (2 ** (i - 1))
                time.sleep(wait)
                continue
            if i == tries:
                raise
            time.sleep(base * (2 ** (i - 1)) * (0.7 + random.random() * 0.6))
        except httpx.HTTPError:
            if i == tries:
                raise
            time.sleep(base * (2 ** (i - 1)) * (0.7 + random.random() * 0.6))
