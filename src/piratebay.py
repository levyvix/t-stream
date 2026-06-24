#! /usr/bin/python
import re
import unicodedata
from typing import Optional, Tuple
from urllib.parse import parse_qs, unquote_plus, urlparse

import requests
from bs4 import BeautifulSoup, Tag

SIZE_RE = re.compile(r"Size\s+(.+?)(?:,|$)")
SIZE_FALLBACK_RE = re.compile(r"(\d+(?:\.\d+)?\s*(?:[KMGTP]i?B))", re.IGNORECASE)
DIGITS_RE = re.compile(r"\d+")


def title_from_magnet(magnet_url: str) -> Optional[str]:
    try:
        dn = parse_qs(urlparse(magnet_url).query).get("dn", [])
        if dn and dn[0].strip():
            return unquote_plus(dn[0]).strip()
    except Exception:
        return None


def parse_size(row, details_text) -> str:
    if details_text:
        match = SIZE_RE.search(details_text.get_text(" ", strip=True))
        return unicodedata.normalize("NFKD", match.group(1)) if match else "Unknown"

    match = SIZE_FALLBACK_RE.search(row.get_text(" ", strip=True))
    return unicodedata.normalize("NFKD", match.group(1)) if match else "Unknown"


def parse_peers(columns) -> Tuple[str, str]:
    numeric = [
        col.get_text(strip=True)
        for col in columns
        if DIGITS_RE.fullmatch(col.get_text(strip=True) or "")
    ]
    if len(numeric) >= 2:
        return numeric[-2], numeric[-1]

    seeders = columns[2].get_text(strip=True) if len(columns) > 2 else "0"
    leeches = columns[3].get_text(strip=True) if len(columns) > 3 else "0"
    return seeders or "0", leeches or "0"


def parse_results(soup: BeautifulSoup) -> dict:
    table = soup.find("table", id="searchResult") or soup.table
    results = {"movie_info": []}
    if not isinstance(table, Tag):
        return results

    for row in table.find_all("tr"):
        columns = row.find_all("td")
        if len(columns) < 4:
            continue

        magnet_link = row.find("a", href=lambda x: x and x.startswith("magnet:"))
        if not magnet_link:
            continue

        title_link = (
            row.select_one("a.detLink")
            or row.select_one("td.detName a")
            or row.find("a", href=lambda x: x and x.startswith("/torrent/"))
        )
        title = title_link.get_text(strip=True) if title_link else ""
        if not title:
            title = title_from_magnet(magnet_link["href"]) or "Unknown title"

        details_text = (
            row.select_one(".detDesc") or row.find("font", class_="detDesc") or row.find("font")
        )
        seeders, leeches = parse_peers(columns)

        results["movie_info"].append(
            {
                "title": title,
                "magnet_url": magnet_link["href"],
                "seeders": seeders,
                "leeches": leeches,
                "size": parse_size(row, details_text),
            }
        )

    return results


def pirate(query: Optional[str] = None) -> dict:
    url = "https://tpb.party/top/200" if not query else f"https://tpb.party/search/{query}"
    try:
        res = requests.get(url, timeout=20)
        res.raise_for_status()
    except requests.RequestException as e:
        raise ValueError(f"Oops! Didn't get valid response: {e}")

    soup = BeautifulSoup(res.content.decode("utf-8"), "html.parser")
    return parse_results(soup)
