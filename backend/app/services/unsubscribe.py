import asyncio
import ipaddress
import re
import socket
from urllib.parse import urlparse

import requests

_URL_RE = re.compile(r"<([^>]+)>")


def parse_list_unsubscribe(header_value: str) -> list[str]:
    return _URL_RE.findall(header_value or "")


def supports_one_click(list_unsubscribe_post: str) -> bool:
    return "one-click" in (list_unsubscribe_post or "").lower()


class UnsafeUnsubscribeUrl(Exception):
    """Raised when a List-Unsubscribe URL resolves to a non-public address.

    The URL comes straight from an untrusted inbound email header, so treating it
    as a safe outbound HTTP target without checking is a server-side request
    forgery (SSRF) hole — a crafted email could point it at an internal service or
    a cloud metadata endpoint (e.g. 169.254.169.254) and have this backend POST to
    it on the user's behalf.
    """


def _assert_public_host(url: str) -> None:
    hostname = urlparse(url).hostname
    if not hostname:
        raise UnsafeUnsubscribeUrl(f"no hostname in {url!r}")
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise UnsafeUnsubscribeUrl(f"could not resolve {hostname!r}") from e
    for info in infos:
        addr = ipaddress.ip_address(info[4][0])
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
            or addr.is_unspecified
        ):
            raise UnsafeUnsubscribeUrl(f"{hostname!r} resolves to non-public address {addr}")


def _one_click_post_sync(url: str) -> bool:
    if not url.lower().startswith("https://"):
        raise UnsafeUnsubscribeUrl("one-click unsubscribe requires an https:// URL")
    _assert_public_host(url)
    # stream=True + no content read: we only need the status code, and this
    # avoids ever buffering a response body from an untrusted server into memory.
    with requests.post(
        url, data={"List-Unsubscribe": "One-Click"}, timeout=10, allow_redirects=False, stream=True
    ) as resp:
        return 200 <= resp.status_code < 300


async def one_click_unsubscribe(url: str) -> bool:
    return await asyncio.to_thread(_one_click_post_sync, url)
