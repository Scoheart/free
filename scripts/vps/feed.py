"""Read the monitor inputs and assemble the public VPS feed."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .normalize import EMAIL_RE, SECRET_RE, as_list, clean_text, latest_beijing
from .offers import clean_free_item, clean_lead, clean_official
from .stock import clean_provider, source_notes


FORBIDDEN_NAMES = {
    "signups.json",
    "signup.json",
    "accounts.json",
    "secrets.json",
    "credentials.json",
}

def read_watch_file(src: Path, name: str) -> dict[str, Any]:
    lowered = name.lower()
    if lowered in FORBIDDEN_NAMES or "signup" in lowered or "credential" in lowered or "secret" in lowered:
        raise SystemExit(f"refusing to read {name}")
    path = src / name
    if not path.is_file():
        raise SystemExit(f"missing {name} in {src}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{name} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{name} must be a JSON object")
    return data

def build_vps(src: Path) -> dict[str, Any]:
    if not src.is_dir():
        raise SystemExit(f"not a directory: {src}")
    # Intentionally do not listdir-and-read. signups.json must never be opened.
    stock = read_watch_file(src, "stock-state.json")
    black_friday = read_watch_file(src, "bf-seen.json")
    free_seen = read_watch_file(src, "free-vps-seen.json")

    stock_at = clean_text(stock.get("scanned_at_beijing"))
    bf_at = clean_text(black_friday.get("scanned_at_beijing"))
    free_at = clean_text(free_seen.get("scanned_at_beijing"))

    dmit = stock.get("dmit") if isinstance(stock.get("dmit"), dict) else {}
    bandwagon = stock.get("bandwagonhost") if isinstance(stock.get("bandwagonhost"), dict) else {}
    if not bandwagon and isinstance(stock.get("bandwagon"), dict):
        bandwagon = stock.get("bandwagon") or {}
    catalogs = [bandwagon.get("catalog_stock_bwg_la"), bandwagon.get("catalog_vpsrestock")]

    free_items = []
    for item in as_list(free_seen.get("items")):
        cleaned = clean_free_item(item)
        if cleaned:
            free_items.append(cleaned)

    official = []
    for entry in as_list(black_friday.get("official")):
        cleaned = clean_official(entry)
        if cleaned:
            official.append(cleaned)
    leads = []
    for entry in as_list(black_friday.get("leads_third_party_only") or black_friday.get("leads")):
        cleaned = clean_lead(entry)
        if cleaned:
            leads.append(cleaned)

    document = {
        "schema_version": 1,
        "sample": False,
        "updated_at_beijing": latest_beijing([stock_at, bf_at, free_at]),
        "scanned_at_beijing": {
            "stock": stock_at,
            "black_friday": bf_at,
            "free_vps": free_at,
        },
        "free_vps": free_items,
        "stock": {
            "source_notes": source_notes(stock.get("source_issues")),
            "providers": [
                clean_provider("dmit", "DMIT", dmit, [], stock_at),
                clean_provider("bandwagonhost", "搬瓦工", bandwagon, catalogs, stock_at),
            ],
        },
        "black_friday": {
            "date_note": clean_text(black_friday.get("black_friday_2026_date_note") or black_friday.get("date_note")),
            "official": official,
            "leads": leads,
        },
    }
    raw = json.dumps(document, ensure_ascii=False)
    if EMAIL_RE.search(raw) or SECRET_RE.search(raw):
        raise SystemExit("refusing to write VPS JSON: output still contains an email or secret-like string")
    return document

def write_vps(document: dict[str, Any], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
