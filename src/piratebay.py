#! /usr/bin/python
import unicodedata
import re
from urllib.parse import parse_qs, unquote_plus, urlparse

import requests
from bs4 import BeautifulSoup

def get_json(soup):
    table = soup.find("table", id="searchResult") or soup.table

    json_obj = {
        "movie_info":[]
    }

    if not table:
        return json_obj

    def title_from_magnet(magnet_url):
        try:
            query = urlparse(magnet_url).query
            dn = parse_qs(query).get("dn", [])
            if dn and dn[0].strip():
                return unquote_plus(dn[0]).strip()
        except Exception:
            return None
        return None

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
            fallback_title = title_from_magnet(magnet_link["href"])
            title = fallback_title if fallback_title else "Unknown title"

        details_text = (
            row.select_one(".detDesc")
            or row.find("font", class_="detDesc")
            or row.find("font")
        )
        size = "Unknown"
        if details_text:
            details = details_text.get_text(" ", strip=True)
            match = re.search(r"Size\s+(.+?)(?:,|$)", details)
            if match:
                size = unicodedata.normalize("NFKD", match.group(1))
        else:
            # Fallback for layouts where size appears directly in cell text.
            row_text = row.get_text(" ", strip=True)
            match = re.search(r"(\d+(?:\.\d+)?\s*(?:[KMGTP]i?B))", row_text, re.IGNORECASE)
            if match:
                size = unicodedata.normalize("NFKD", match.group(1))

        numeric_cells = [
            col.get_text(strip=True)
            for col in columns
            if re.fullmatch(r"\d+", col.get_text(strip=True) or "")
        ]
        if len(numeric_cells) >= 2:
            seeders = numeric_cells[-2]
            leeches = numeric_cells[-1]
        else:
            seeders = columns[2].get_text(strip=True) if len(columns) > 2 else "0"
            leeches = columns[3].get_text(strip=True) if len(columns) > 3 else "0"
            if not seeders:
                seeders = "0"
            if not leeches:
                leeches = "0"

        json_obj["movie_info"].append({
            "title": title,
            "magnet_url": magnet_link["href"],
            "seeders": seeders,
            "leeches": leeches,
            "size": size,
        })

    return json_obj

def pirate(query = None):
    if not query:
        url = "https://tpb.party/top/200"
    else:
        url = f"https://tpb.party/search/{query}"
    res = requests.get(url)
    if res.status_code != 200:
        raise ValueError("Ops didn't get valid response")
    content = res.content
    soup = BeautifulSoup(content , "html.parser")
    obj = get_json(soup)
    return obj
