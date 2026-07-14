from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.retrieval.adapters.base import ExternalProblemCandidate, RetrievalAdapter
from app.retrieval.compliance import get_policy


class UnsafeURL(ValueError): pass


def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeURL("Only absolute HTTP(S) URLs are allowed")
    if parsed.hostname in {"localhost", "host.docker.internal"} or "." not in parsed.hostname:
        raise UnsafeURL("Local and Docker service hostnames are prohibited")
    for item in socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM):
        address = ipaddress.ip_address(item[4][0])
        if not address.is_global:
            raise UnsafeURL("URL resolves to a non-public address")


class UserURLAdapter(RetrievalAdapter):
    name = "user_url"

    def __init__(self, urls: list[str] | None = None):
        self.urls = urls or []

    def discover(self, query: str, *, limit: int) -> list[ExternalProblemCandidate]:
        settings = get_settings()
        policy = get_policy(self.name)
        results = []
        for url in self.urls[:limit]:
            current = url
            for _ in range(settings.external_fetch_max_redirects + 1):
                validate_public_url(current)
                with httpx.stream("GET", current, timeout=settings.external_fetch_timeout_seconds, follow_redirects=False, headers={"user-agent": "CodingHelper/1.0"}) as response:
                    if response.is_redirect:
                        current = urljoin(current, response.headers.get("location", ""))
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").casefold()
                    if "text/html" not in content_type and "text/plain" not in content_type:
                        raise ValueError("Unsupported content type")
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > settings.external_fetch_max_bytes:
                            raise ValueError("Response exceeds configured size limit")
                    text = _safe_text(bytes(body).decode(response.encoding or "utf-8", errors="replace"))
                    results.append(ExternalProblemCandidate(title=urlparse(current).hostname or "User source", url=current, source_name=self.name, source_tier=4, statement_text=text[: policy.max_chars_to_store], attribution=current, retrieval_method="user_supplied_ssrf_safe", storage_capability="snippet"))
                    break
            else:
                raise ValueError("Too many redirects")
        return results


def _safe_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "aside", "form"]): tag.decompose()
    for tag in soup.select('[hidden], [aria-hidden="true"], [style*="display:none"], [style*="display: none"]'): tag.decompose()
    return "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
