"""The sources of an answer, as stored by the engine, read and listed for the report."""

import json
from typing import Any

from app.exports.markdown import esc


def parse_sources(raw_sources: Any) -> list[dict[str, Any]]:
    """Normalise the sources field into a flat list of source dicts.

    Mirrors the frontend parser (useSourceParser): sources may arrive as a
    JSON string, a dict grouped by files/web/webUrls/webSearchQueries, or a
    list of items (file_search with a `filenames` array, web/web_search,
    or plain strings).
    """
    if not raw_sources:
        return []
    parsed = raw_sources
    if isinstance(raw_sources, str):
        try:
            parsed = json.loads(raw_sources)
        except (json.JSONDecodeError, TypeError):
            return [{"type": "file", "filename": raw_sources}]

    items = []
    if isinstance(parsed, dict):
        for key, default_type in (
            ("files", "file"),
            ("web", "web"),
            ("webUrls", "web"),
            ("webSearchQueries", "web_search"),
        ):
            group = parsed.get(key)
            if isinstance(group, list):
                for it in group:
                    if isinstance(it, dict):
                        items.append({**it, "type": it.get("type", default_type)})
                    elif isinstance(it, str):
                        field = "filename" if default_type == "file" else "url"
                        items.append({"type": default_type, field: it})
        if not items:
            items.append(parsed)  # a single source object
    elif isinstance(parsed, list):
        items = list(parsed)
    else:
        return []

    # Expand file_search entries (which carry several filenames) and
    # default the type for anything missing one.
    normalised = []
    for src in items:
        if isinstance(src, str):
            if src.startswith("http"):
                normalised.append({"type": "web", "url": src})
            else:
                normalised.append({"type": "file", "filename": src})
        elif isinstance(src, dict):
            if src.get("type") == "file_search":
                filenames = src.get("filenames") or (
                    [src["filename"]] if src.get("filename") else []
                )
                for fn in filenames:
                    normalised.append({"type": "file_search", "filename": fn})
            else:
                normalised.append(
                    {
                        **src,
                        "type": src.get("type") or ("web" if src.get("url") else "file"),
                    }
                )
    return normalised


def format_sources(raw_sources: Any) -> list[str]:
    """Build numbered, reportlab-ready source lines (links for web sources)."""
    lines, seen = [], set()
    for src in parse_sources(raw_sources):
        stype = src.get("type", "")
        if stype in ("web", "web_search"):
            url = src.get("url") or src.get("content")
            if not url or url in seen:
                continue
            seen.add(url)
            href = esc(url)
            # Drop noisy tracking params from the visible text, keep full link
            display = url.split("?")[0] if "utm_" in url else url
            lines.append(f'Web &mdash; <a href="{href}" color="#1F66B0">{esc(display)}</a>')
        elif stype in ("file", "file_search"):
            name = src.get("filename") or src.get("content")
            if not name or ("file", name) in seen:
                continue
            seen.add(("file", name))
            lines.append(f"Document &mdash; {esc(name)}")
        else:
            value = src.get("url") or src.get("filename") or src.get("content")
            if not value or value in seen:
                continue
            seen.add(value)
            lines.append(esc(value))

    return [f"{i}. {line}" for i, line in enumerate(lines, 1)]
