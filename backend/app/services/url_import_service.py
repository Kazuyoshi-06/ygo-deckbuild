import base64
import re
import struct
from urllib.parse import urlparse

import httpx

from app.services.ydk_parser import ParsedYdk, parse as parse_ydk

_YDKE_RE = re.compile(r'ydke://([A-Za-z0-9+/=]*)!([A-Za-z0-9+/=]*)!([A-Za-z0-9+/=]*)!?')
_TITLE_RE = re.compile(r'<title[^>]*>([^<]{1,200})</title>', re.IGNORECASE)
_YDK_LINK_RE = re.compile(r'''href=['"]([^'"]*\.ydk[^'"]*)['"]''', re.IGNORECASE)
_MAX_RESPONSE = 2 * 1024 * 1024  # 2 MB
_TITLE_SUFFIXES = (
    ' - YGOPRODeck', ' | YGOPRODeck', ' – YGOPRODeck',
    ' - Yu-Gi-Oh!', ' | Yu-Gi-Oh!', ' - YGOPRO', ' | YGOPRO',
)


def _decode_section(b64: str) -> list[int]:
    if not b64:
        return []
    padding = (4 - len(b64) % 4) % 4
    raw = base64.b64decode(b64 + '=' * padding)
    count = len(raw) // 4
    return [struct.unpack_from('<I', raw, i * 4)[0] for i in range(count)]


def parse_ydke(url: str) -> ParsedYdk:
    """Parse a ydke:// URL into card ID lists.

    Format: ydke://[main_b64]![extra_b64]![side_b64]!
    Each section is base64-encoded little-endian uint32 passcodes.
    """
    m = _YDKE_RE.match(url.strip())
    if not m:
        raise ValueError("Invalid YDKE URL — expected ydke://[main]![extra]![side]!")
    return ParsedYdk(
        main=_decode_section(m.group(1)),
        extra=_decode_section(m.group(2)),
        side=_decode_section(m.group(3)),
    )


def _clean_title(html: str) -> str:
    m = _TITLE_RE.search(html)
    if not m:
        return ''
    title = m.group(1).strip()
    for suffix in _TITLE_SUFFIXES:
        if title.endswith(suffix):
            title = title[: -len(suffix)]
    return title[:200].strip()


async def import_from_url(url: str) -> tuple[ParsedYdk, str]:
    """Fetch a deck from a URL and return (ParsedYdk, title_hint).

    Supported inputs:
    - ydke:// URLs (YDKE format used by Omega, Dueling Nexus, YGOProDeck builder)
    - Direct .ydk file URLs (any HTTP host)
    - HTML pages with an embedded ydke:// link or a .ydk download link
    """
    url = url.strip()

    if url.lower().startswith('ydke://'):
        return parse_ydke(url), ''

    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("URL must start with http://, https://, or ydke://")

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=12.0,
        headers={'User-Agent': 'Mozilla/5.0 YGO-Intel/1.0 deck-importer'},
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()

        content = resp.content[:_MAX_RESPONSE]
        content_type = resp.headers.get('content-type', '').lower()

        # Direct .ydk file URL or plain-text response
        is_ydk_path = parsed.path.lower().endswith('.ydk')
        if is_ydk_path or 'text/plain' in content_type:
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                text = content.decode('latin-1')
            deck = parse_ydk(text)
            if deck.is_empty:
                raise ValueError("The file at this URL contains no card IDs")
            fname = parsed.path.rsplit('/', 1)[-1]
            title = fname.removesuffix('.ydk').removesuffix('.YDK') if is_ydk_path else ''
            return deck, title

        # HTML page — search for embedded YDKE or a .ydk download link
        if 'text/html' in content_type or not content_type:
            html = content.decode('utf-8', errors='replace')

            m = _YDKE_RE.search(html)
            if m:
                deck = parse_ydke(m.group(0))
                if not deck.is_empty:
                    return deck, _clean_title(html)

            for link_match in _YDK_LINK_RE.finditer(html):
                href = link_match.group(1)
                if not href.startswith('http'):
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"
                try:
                    ydk_resp = await client.get(href)
                    ydk_resp.raise_for_status()
                    deck = parse_ydk(ydk_resp.text)
                    if not deck.is_empty:
                        return deck, _clean_title(html)
                except Exception:
                    continue

            raise ValueError(
                "Could not extract deck data from this page. "
                "Try: (1) the direct .ydk download URL, "
                "or (2) a ydke:// URL from the YGOProDeck deck builder "
                "(Share → Copy YDKE Link)."
            )

        raise ValueError(
            f"Unexpected content type '{content_type}'. "
            "Please provide a .ydk file URL or a ydke:// URL."
        )
