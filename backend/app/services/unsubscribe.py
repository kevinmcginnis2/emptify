import asyncio
import re

import requests

_URL_RE = re.compile(r"<([^>]+)>")


def parse_list_unsubscribe(header_value: str) -> list[str]:
    return _URL_RE.findall(header_value or "")


def supports_one_click(list_unsubscribe_post: str) -> bool:
    return "one-click" in (list_unsubscribe_post or "").lower()


def _one_click_post_sync(url: str) -> bool:
    resp = requests.post(url, data={"List-Unsubscribe": "One-Click"}, timeout=10)
    return 200 <= resp.status_code < 300


async def one_click_unsubscribe(url: str) -> bool:
    return await asyncio.to_thread(_one_click_post_sync, url)
