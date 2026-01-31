#!/usr/bin/env python3
"""
Build a local cache of filtered philosopher quotes to avoid slow API calls at runtime.

Usage:
  python scripts/build_philo_quote_cache.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import requests

BASE_URL = "https://philosophersapi.com"
QUOTES_INDEX = f"{BASE_URL}/api/quotes"
OUT_PATH = Path("data/philo_quotes_cache.json")
TIMEOUT = 15

ALLOWED_SCHOOLS = {
    "Aristotelianism",
    "Cynicism",
    "Platonism",
    "Pre-Socratic",
    "Pythagoreanism",
    "Stoicism",
    "Neo-Platonism",
    "Neoplatonism",
    "Classical Greek",
}


def get_json(url: str) -> Any:
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _norm_url(u: str) -> str:
    if not u:
        return ""
    u = str(u).strip()
    if u.startswith("http://") or u.startswith("https://"):
        return u
    if u.startswith("//"):
        return "https:" + u
    if not u.startswith("/"):
        u = "/" + u
    return BASE_URL + u


def _extract_image_value(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("url", "src", "path", "image", "imageUrl", "imageURL", "imagePath"):
            if key in value:
                return value.get(key)
    if isinstance(value, list):
        for item in value:
            found = _extract_image_value(item)
            if found:
                return found
    return ""


def _pick_image_from_images(images: dict) -> str:
    if not isinstance(images, dict):
        return ""
    preferred_keys = [
        "full1200x1600",
        "full840x1120",
        "full600x800",
        "ill750x750",
        "ill500x500",
        "ill250x250",
        "thumbnailIll150x150",
        "thumbnailIll50x50",
    ]
    for key in preferred_keys:
        if key in images:
            found = _extract_image_value(images.get(key))
            if found:
                return found
    for _, value in images.items():
        found = _extract_image_value(value)
        if found:
            return found
    return ""


def extract_card(detail: dict) -> dict:
    quote = detail.get("quote") or detail.get("text") or detail.get("content") or ""
    quote = str(quote).strip()

    ph = detail.get("philosopher") or detail.get("author") or {}
    name = ph.get("name") or ph.get("fullName") or detail.get("philosopherName") or "Philosophy"
    school = ph.get("school") or detail.get("school") or ""

    images = ph.get("images") or {}
    img = (
        ph.get("image")
        or ph.get("imageUrl")
        or ph.get("imageURL")
        or ph.get("imagePath")
        or detail.get("image")
        or detail.get("imageUrl")
        or detail.get("imageURL")
        or detail.get("imagePath")
        or images.get("face")
        or images.get("portrait")
        or images.get("full")
        or images.get("lg")
        or images.get("md")
        or images.get("sm")
        or images.get("thumb")
        or images.get("thumbnail")
    )
    if not img:
        img = _pick_image_from_images(images)
    image_url = _norm_url(img)

    quote_date = (
        detail.get("date")
        or detail.get("quoteDate")
        or detail.get("year")
        or detail.get("spokenOn")
        or detail.get("saidOn")
        or detail.get("published")
    )
    if isinstance(quote_date, dict):
        year = quote_date.get("year") or quote_date.get("y")
        month = quote_date.get("month") or quote_date.get("m")
        day = quote_date.get("day") or quote_date.get("d")
        parts = [str(p) for p in (day, month, year) if p]
        quote_date = " ".join(parts)
    quote_date = str(quote_date).strip() if quote_date else ""

    return {
        "name": str(name).strip(),
        "quote": quote,
        "image_url": image_url,
        "quote_date": quote_date,
        "school": str(school).strip(),
    }


def main() -> None:
    print("Fetching quotes index...")
    idx = get_json(QUOTES_INDEX)
    if not isinstance(idx, list):
        raise RuntimeError("Unexpected quotes index payload.")

    results: List[Dict[str, Any]] = []
    total = len(idx)
    print(f"Processing {total} quotes...")
    for item in idx:
        qid = item.get("id") or item.get("_id") or item.get("quoteID") or item.get("quoteId")
        if not qid:
            continue
        print(f"- fetching quote {qid}")
        detail = get_json(f"{BASE_URL}/api/quotes/{qid}")
        card = extract_card(detail)
        if card.get("school") in ALLOWED_SCHOOLS and card.get("quote"):
            results.append(card)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(results)} quotes to {OUT_PATH}")
    print("Done.")


if __name__ == "__main__":
    main()
