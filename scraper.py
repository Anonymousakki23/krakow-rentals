"""Pure scraping and parsing helpers for the Kraków rental aggregator.

This module has no Streamlit dependency so the parsing logic can be unit
tested without running the UI.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from dataclasses import dataclass
from typing import Iterable, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 20
USER_AGENT = "krakow-rentals/1.0 (+https://github.com/Anonymousakki23/krakow-rentals)"
SCRAPER_API_ENDPOINT = "https://api.scraperapi.com/"

DISTRICTS = {
    "Stare Miasto": {"olx": "stare-miasto", "otodom": "stare-miasto"},
    "Grzegórzki": {"olx": "grzegorzki", "otodom": "grzegorzki"},
    "Prądnik Czerwony": {"olx": "pradnik-czerwony", "otodom": "pradnik-czerwony"},
    "Krowodrza": {"olx": "krowodrza", "otodom": "krowodrza"},
    "Ruczaj / Dębniki": {"olx": "debniki", "otodom": "debniki"},
    "Podgórze": {"olx": "podgorze", "otodom": "podgorze"},
}


@dataclass(frozen=True)
class Listing:
    source: str
    title: str
    price_pln: int
    url: str


def parse_price(text: str) -> Optional[int]:
    """Extract an integer PLN price from strings like "3 200 zł" or "3200zl".

    Returns None when no digits are present.
    """
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def normalize_url(url: str) -> str:
    """Normalize listing URLs for deduplication."""
    if not url:
        return ""
    parts = urllib.parse.urlsplit(url)
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit((parts.scheme, netloc, path, "", ""))


def olx_search_url(slug: str) -> str:
    return (
        "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/krakow/"
        f"q-{slug}/?search%5Bsort_by%5D=price%3Aasc"
    )


def otodom_search_url(slug: str) -> str:
    return f"https://www.otodom.pl/pl/wyniki/wynajem/mieszkanie/malopolskie/krakow/{slug}"


def fetch_html(target_url: str, api_key: str, timeout: int = REQUEST_TIMEOUT) -> Optional[str]:
    """Fetch a page through the configured proxy service.

    Returns the HTML text, or None when the request fails. Raises ValueError
    when no API key is configured.
    """
    if not api_key:
        raise ValueError("SCRAPER_API_KEY is not configured")
    payload = {"api_key": api_key, "url": target_url}
    proxy_url = SCRAPER_API_ENDPOINT + "?" + urllib.parse.urlencode(payload)
    try:
        response = requests.get(
            proxy_url,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        logger.warning("Proxy request failed for %s: %s", target_url, exc)
        return None


def parse_olx(html: str) -> list[Listing]:
    """Parse OLX search-result HTML into listings."""
    soup = BeautifulSoup(html or "", "html.parser")
    cards = soup.find_all("div", {"data-cy": "l-card"})
    results: list[Listing] = []
    for card in cards:
        try:
            title_el = card.find("h6")
            price_el = card.find("p", {"data-testid": "ad-price"})
            link_el = card.find("a", href=True)
            if title_el is None or price_el is None or link_el is None:
                continue
            price = parse_price(price_el.get_text(" ", strip=True))
            if price is None:
                continue
            url = urllib.parse.urljoin("https://www.olx.pl", link_el["href"])
            results.append(
                Listing(
                    source="OLX",
                    title=title_el.get_text(" ", strip=True),
                    price_pln=price,
                    url=url,
                )
            )
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            logger.debug("Skipping malformed OLX card: %s", exc)
            continue
    return results


def parse_otodom(html: str) -> list[Listing]:
    """Parse Otodom search-result HTML into listings."""
    soup = BeautifulSoup(html or "", "html.parser")
    items = soup.find_all("article", {"data-testid": "listing-item"})
    results: list[Listing] = []
    for item in items:
        try:
            title_el = item.find("p", {"data-testid": "title"})
            price_el = item.find("span", {"data-testid": "price"})
            link_el = item.find("a", href=True)
            if title_el is None or price_el is None or link_el is None:
                continue
            price = parse_price(price_el.get_text(" ", strip=True))
            if price is None:
                continue
            url = urllib.parse.urljoin("https://www.otodom.pl", link_el["href"])
            results.append(
                Listing(
                    source="Otodom",
                    title=title_el.get_text(" ", strip=True),
                    price_pln=price,
                    url=url,
                )
            )
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            logger.debug("Skipping malformed Otodom item: %s", exc)
            continue
    return results


def dedupe_listings(listings: Iterable[Listing]) -> list[Listing]:
    """Remove duplicates, preferring the first occurrence."""
    seen: set[str] = set()
    unique: list[Listing] = []
    for listing in listings:
        key = normalize_url(listing.url)
        if not key:
            key = f"{listing.source}|{listing.title.lower()}|{listing.price_pln}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(listing)
    return unique


def filter_by_budget(listings: Iterable[Listing], max_budget: int) -> list[Listing]:
    """Keep listings at or below max_budget, sorted by ascending price."""
    filtered = [listing for listing in listings if listing.price_pln <= max_budget]
    return sorted(filtered, key=lambda item: item.price_pln)
