#!/usr/bin/env python3
"""
Inspect philosophers data from philosophersapi.com.

- Prints all unique schools across philosophers.
- Prints the full JSON tree for Plato (default).
- Recursively lists all attribute paths.
- Extracts image URLs and generates an HTML gallery + downloads images locally.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import requests

BASE_URL = "https://philosophersapi.com"
PHILOSOPHERS_ENDPOINT = f"{BASE_URL}/api/philosophers"
TIMEOUT = 20

OUT_DIR = Path("out")
IMG_DIR = OUT_DIR / "plato_images"
GALLERY_PATH = OUT_DIR / "gallery_plato.html"

# loose URL regex (handles http/https)
URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def fetch_json(url: str) -> Any:
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def normalize_philosophers(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("philosophers", "data", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    raise ValueError("Unexpected philosophers payload shape.")


def collect_unique_schools(philosophers: List[Dict[str, Any]]) -> List[str]:
    schools = set()
    for ph in philosophers:
        school = ph.get("school") or ph.get("schools")
        if isinstance(school, list):
            for s in school:
                if s:
                    schools.add(str(s).strip())
        elif school:
            schools.add(str(school).strip())
    return sorted(s for s in schools if s)


def _matches_name(ph: Dict[str, Any], name: str) -> bool:
    name_l = name.lower()
    for key in ("name", "wikiTitle", "fullName"):
        value = ph.get(key)
        if isinstance(value, str) and value.lower() == name_l:
            return True
    return False


def pick_philosopher(
    philosophers: List[Dict[str, Any]],
    philosopher_id: Optional[str],
    philosopher_name: Optional[str],
) -> Optional[Dict[str, Any]]:
    if philosopher_id:
        for ph in philosophers:
            if str(ph.get("id") or ph.get("_id") or "").strip() == philosopher_id:
                return ph

    if philosopher_name:
        for ph in philosophers:
            if _matches_name(ph, philosopher_name):
                return ph

    return None


def print_attribute_paths(obj: Any, prefix: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_prefix = f"{prefix}.{k}" if prefix else k
            print_attribute_paths(v, new_prefix)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_prefix = f"{prefix}[{i}]"
            print_attribute_paths(item, new_prefix)
    else:
        print(prefix)


def is_url(s: str) -> bool:
    return bool(URL_RE.match(s.strip()))


def collect_urls_under_key(obj: Any, target_key: str) -> List[Tuple[str, str]]:
    """
    Collect (path, url) for any string URL found inside dicts/lists whose
    parent key matches target_key.
    """
    found: List[Tuple[str, str]] = []

    def rec(x: Any, path: str, under_target: bool) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                new_under = under_target or (k == target_key)
                new_path = f"{path}.{k}" if path else k
                rec(v, new_path, new_under)
        elif isinstance(x, list):
            for i, item in enumerate(x):
                rec(item, f"{path}[{i}]", under_target)
        else:
            if under_target and isinstance(x, str) and is_url(x):
                found.append((path, x))

    rec(obj, "", False)
    return found


def collect_any_urls(obj: Any) -> List[Tuple[str, str]]:
    """Fallback: collect any URL-like strings anywhere in the JSON."""
    found: List[Tuple[str, str]] = []

    def rec(x: Any, path: str) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                new_path = f"{path}.{k}" if path else k
                rec(v, new_path)
        elif isinstance(x, list):
            for i, item in enumerate(x):
                rec(item, f"{path}[{i}]")
        else:
            if isinstance(x, str) and is_url(x):
                found.append((path, x))

    rec(obj, "")
    return found


def safe_filename_from_url(url: str, fallback_index: int) -> str:
    parsed = urlparse(url)
    name = os.path.basename(parsed.path)
    if not name or "." not in name:
        name = f"image_{fallback_index:03d}.jpg"
    # sanitize
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    return name


def download_image(url: str, out_path: Path) -> bool:
    try:
        r = requests.get(url, timeout=TIMEOUT, stream=True)
        r.raise_for_status()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 64):
                if chunk:
                    f.write(chunk)
        return True
    except Exception:
        return False


def write_gallery(items: List[Dict[str, str]], gallery_path: Path) -> None:
    gallery_path.parent.mkdir(parents=True, exist_ok=True)

    cards = []
    for item in items:
        badge = (
            '<span class="badge">downloaded</span>'
            if item.get("downloaded") == "yes"
            else '<span class="badge">remote</span>'
        )

        cards.append(
            f"""
    <div class="card">
      <div class="imgwrap">
        <img src="{item['src']}" alt="Plato image"/>
      </div>
      <div class="info">
        <div class="path">{item['path']}</div>
        <div class="link">
          <a href="{item['url']}" target="_blank" rel="noreferrer">source</a>
          {badge}
        </div>
      </div>
    </div>
"""
        )

    cards_html = "".join(cards)

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Plato — Image Gallery</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; }}
    h1 {{ margin-bottom: 8px; }}
    .meta {{ color: #555; margin-bottom: 18px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 14px;
    }}
    .card {{
      border: 1px solid #ddd;
      border-radius: 12px;
      overflow: hidden;
      background: #fff;
      box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }}
    .imgwrap {{ aspect-ratio: 1 / 1; background: #f6f6f6; display:flex; align-items:center; justify-content:center; }}
    img {{ width: 100%; height: 100%; object-fit: cover; display:block; }}
    .info {{ padding: 10px 12px; font-size: 13px; }}
    .path {{ color: #333; font-weight: 600; margin-bottom: 6px; word-break: break-word; }}
    .link a {{ color: #0b5; text-decoration: none; word-break: break-word; }}
    .link a:hover {{ text-decoration: underline; }}
    .badge {{ display:inline-block; padding:2px 8px; border-radius:999px; background:#eef; color:#224; font-size:12px; margin-left:6px; }}
  </style>
</head>
<body>
  <h1>Plato — Image Gallery</h1>
  <div class="meta">{len(items)} image URLs found</div>

  <div class="grid">
{cards_html}
  </div>
</body>
</html>
"""
    gallery_path.write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect philosophers API data.")
    parser.add_argument("--id", dest="philosopher_id", help="Exact philosopher id to print.")
    parser.add_argument("--name", dest="philosopher_name", help="Exact philosopher name to print.")
    parser.add_argument(
        "--endpoint",
        default=PHILOSOPHERS_ENDPOINT,
        help=f"Philosophers list endpoint (default: {PHILOSOPHERS_ENDPOINT})",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Do not download images; gallery will reference remote URLs only.",
    )
    args = parser.parse_args()

    philosopher_name = args.philosopher_name or "Plato"

    try:
        payload = fetch_json(args.endpoint)
        philosophers = normalize_philosophers(payload)

        schools = collect_unique_schools(philosophers)
        print("Unique schools:")
        for s in schools:
            print(f"- {s}")

        ph = pick_philosopher(philosophers, args.philosopher_id, philosopher_name)
        print(f"\nPhilosopher detail ({philosopher_name}):")
        if not ph:
            print(f"({philosopher_name} not found.)")
            return

        print("\n--- RAW JSON ---")
        print(json.dumps(ph, indent=2, ensure_ascii=False))

        print("\n--- ATTRIBUTE PATHS ---")
        print_attribute_paths(ph)

        # 1) Prefer URLs under images subtree
        image_urls = collect_urls_under_key(ph, "images")

        # 2) If none found, fall back to ANY urls
        if not image_urls:
            print("\n(No URLs found under key 'images'. Falling back to any URLs in JSON.)")
            image_urls = collect_any_urls(ph)

        # De-duplicate while preserving order
        seen: Set[str] = set()
        dedup: List[Tuple[str, str]] = []
        for path, url in image_urls:
            if url not in seen:
                seen.add(url)
                dedup.append((path, url))

        if not dedup:
            print("\nNo image URLs found.")
            return

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        IMG_DIR.mkdir(parents=True, exist_ok=True)

        gallery_items: List[Dict[str, str]] = []
        print(f"\nFound {len(dedup)} unique image URL(s).")

        for idx, (path, url) in enumerate(dedup, start=1):
            filename = safe_filename_from_url(url, idx)
            local_path = IMG_DIR / filename

            downloaded = "no"
            src = url  # default: remote

            if not args.no_download:
                ok = download_image(url, local_path)
                if ok:
                    downloaded = "yes"
                    # Make src relative for the HTML gallery
                    src = str(local_path.relative_to(OUT_DIR)).replace("\\", "/")
                else:
                    # keep remote if download failed
                    downloaded = "no"
                    src = url

            gallery_items.append(
                {
                    "path": path,
                    "url": url,
                    "src": src,
                    "downloaded": downloaded,
                }
            )

        write_gallery(gallery_items, GALLERY_PATH)

        print("\nGallery generated:")
        print(f"- {GALLERY_PATH.resolve()}")
        if not args.no_download:
            print(f"Images saved under: {IMG_DIR.resolve()}")
        print("\nOpen the HTML file in your browser to visualize all images.")

    except requests.RequestException as e:
        print("HTTP error calling philosophers API:", e)
        sys.exit(1)
    except Exception as e:
        print("Error:", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
