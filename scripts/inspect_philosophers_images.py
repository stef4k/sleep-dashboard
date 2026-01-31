#!/usr/bin/env python3
"""
Fetch philosopher details (default: Plato) from philosophersapi.com,
download all image assets, and generate an HTML gallery.

Uses the documented endpoints:
  /api/philosophers/name/<Name>
  /api/philosophers/<UUID>
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests

BASE_URL = "https://philosophersapi.com"
TIMEOUT = 20

OUT_DIR = Path("out")
IMG_DIR = OUT_DIR / "philosopher_images"
GALLERY_PATH = OUT_DIR / "gallery.html"

# Accept absolute URLs OR the API's relative image paths (/Images/...)
ABS_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
REL_IMG_RE = re.compile(r"^/images/", re.IGNORECASE)


def fetch_json(url: str) -> Any:
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def to_absolute(url_or_path: str) -> str:
    s = (url_or_path or "").strip()
    if not s:
        return s
    if ABS_URL_RE.match(s):
        return s
    # API returns "/Images/..." paths
    if s.startswith("/"):
        return urljoin(BASE_URL, s)
    # If it’s something odd, still try to join
    return urljoin(BASE_URL + "/", s)


def extract_image_items(images_obj: Any) -> List[Tuple[str, str]]:
    """
    Extract (path_label, absolute_url) from the API images dict.
    Example returned paths:
      illustrations.ill500x500
      faceImages.face250x250
    """
    items: List[Tuple[str, str]] = []

    def rec(x: Any, prefix: str = "") -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                new_prefix = f"{prefix}.{k}" if prefix else k
                rec(v, new_prefix)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                rec(v, f"{prefix}[{i}]")
        else:
            if isinstance(x, str) and x.strip():
                # Keep only plausible image paths/urls
                s = x.strip()
                if ABS_URL_RE.match(s) or s.startswith("/"):
                    items.append((prefix, to_absolute(s)))

    rec(images_obj, "")
    # de-dupe by url, keep first label
    seen = set()
    out = []
    for label, url in items:
        if url and url not in seen:
            seen.add(url)
            out.append((label, url))
    return out


def safe_name_from_url(url: str, fallback_index: int) -> str:
    parsed = urlparse(url)
    name = os.path.basename(parsed.path)
    if not name:
        name = f"image_{fallback_index:03d}"
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    return name


def download_image(url: str, out_path: Path) -> Optional[Path]:
    """
    Download url if it's truly an image. Returns final saved path, or None.
    Fixes extension based on Content-Type.
    """
    try:
        r = requests.get(url, timeout=TIMEOUT, stream=True, allow_redirects=True)
        r.raise_for_status()

        ctype = (r.headers.get("Content-Type") or "").lower()
        if not ctype.startswith("image/"):
            # You were previously saving HTML error pages as .jpg; stop doing that.
            head = r.text[:160].replace("\n", " ").replace("\r", " ")
            print(f"[SKIP] Not an image: {url}")
            print(f"       Content-Type={ctype!r} BodyStarts={head!r}")
            return None

        ext_map = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "image/svg+xml": ".svg",
        }
        base_ctype = ctype.split(";")[0].strip()
        ext = ext_map.get(base_ctype, out_path.suffix or ".img")

        final_path = out_path
        if final_path.suffix.lower() != ext:
            final_path = out_path.with_suffix(ext)

        final_path.parent.mkdir(parents=True, exist_ok=True)
        with open(final_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 64):
                if chunk:
                    f.write(chunk)

        return final_path
    except Exception as e:
        print(f"[FAIL] {url} -> {e}")
        return None


def write_gallery(title: str, items: List[Dict[str, str]], gallery_path: Path) -> None:
    gallery_path.parent.mkdir(parents=True, exist_ok=True)

    cards = []
    for it in items:
        badge = (
            '<span class="badge">downloaded</span>'
            if it.get("downloaded") == "yes"
            else '<span class="badge">remote</span>'
        )
        cards.append(
            f"""
    <div class="card">
      <div class="imgwrap">
        <img src="{html.escape(it['src'])}" alt="image"/>
      </div>
      <div class="info">
        <div class="path">{html.escape(it['label'])}</div>
        <div class="link">
          <a href="{html.escape(it['url'])}" target="_blank" rel="noreferrer">source</a>
          {badge}
        </div>
      </div>
    </div>
"""
        )

    cards_html = "".join(cards)

    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(title)} — Image Gallery</title>
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
  <h1>{html.escape(title)} — Image Gallery</h1>
  <div class="meta">{len(items)} image URLs found</div>

  <div class="grid">
{cards_html}
  </div>
</body>
</html>
"""
    gallery_path.write_text(page, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="Plato", help="Philosopher name (e.g., Plato, John+Locke)")
    parser.add_argument("--id", default=None, help="Philosopher UUID (overrides --name)")
    parser.add_argument("--no-download", action="store_true", help="Do not download; use remote URLs only")
    args = parser.parse_args()

    if args.id:
        url = f"{BASE_URL}/api/philosophers/{args.id}"
        title = args.id
    else:
        url = f"{BASE_URL}/api/philosophers/name/{args.name}"
        title = args.name.replace("+", " ")

    data = fetch_json(url)
    images_obj = data.get("images", {})
    image_items = extract_image_items(images_obj)

    if not image_items:
        print("No images found in philosopher details. Printing 'images' field:")
        print(images_obj)
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    gallery_items: List[Dict[str, str]] = []
    for idx, (label, img_url) in enumerate(image_items, start=1):
        src = img_url
        downloaded = "no"

        if not args.no_download:
            fname = safe_name_from_url(img_url, idx)
            saved = download_image(img_url, IMG_DIR / fname)
            if saved is not None:
                downloaded = "yes"
                src = str(saved.relative_to(OUT_DIR)).replace("\\", "/")

        gallery_items.append(
            {"label": label, "url": img_url, "src": src, "downloaded": downloaded}
        )

    write_gallery(title, gallery_items, GALLERY_PATH)
    print(f"Gallery: {GALLERY_PATH.resolve()}")
    if not args.no_download:
        print(f"Images folder: {IMG_DIR.resolve()}")


if __name__ == "__main__":
    main()
