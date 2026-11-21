"""Normalize free VPS offers and Black Friday entries."""

from __future__ import annotations

import re
from typing import Any

from .normalize import (
    as_bool, as_list, clean_text, clean_url, config_line, norm_compact, price_text,
    spec_label, specs_from,
)


TYPE_LABELS = {
    "always free": ("always_free", "一直免费"),
    "always_free": ("always_free", "一直免费"),
    "free": ("always_free", "一直免费"),
    "free forever": ("always_free", "一直免费"),
    "forever free": ("always_free", "一直免费"),
    "trial": ("trial", "试用额度"),
    "trial credit": ("trial", "试用额度"),
    "free trial": ("trial", "试用额度"),
    "credit": ("trial", "试用额度"),
    "student": ("student", "学生额度"),
    "student credit": ("student", "学生额度"),
    "education": ("student", "学生额度"),
    "github student": ("student", "学生额度"),
    "paas": ("paas", "非 root 的 PaaS"),
    "paas non root": ("paas", "非 root 的 PaaS"),
    "non root paas": ("paas", "非 root 的 PaaS"),
    "non root": ("paas", "非 root 的 PaaS"),
    "一直免费": ("always_free", "一直免费"),
    "试用额度": ("trial", "试用额度"),
    "学生额度": ("student", "学生额度"),
    "非 root 的 paas": ("paas", "非 root 的 PaaS"),
}

def classify_type(value: Any) -> tuple[str, str]:
    raw = clean_text(value)
    if not raw:
        return "other", "其他"
    key = raw.casefold().replace("-", " ").replace("_", " ")
    key = re.sub(r"\s+", " ", key).strip()
    if key in TYPE_LABELS:
        return TYPE_LABELS[key]
    if "学生" in raw:
        return "student", "学生额度"
    if "试用" in raw:
        return "trial", "试用额度"
    if "paas" in key or "非 root" in raw or "非root" in raw.casefold():
        return "paas", "非 root 的 PaaS"
    if "always" in key or "一直" in raw:
        return "always_free", "一直免费"
    if len(raw) <= 24:
        return "other", raw
    return "other", "其他"

def classify_status(status: str, orderable: bool | None) -> tuple[str, str]:
    folded = status.casefold().replace("-", "_").replace(" ", "_")
    if "no_black_friday" in folded or "not_this_year" in folded or "no_sale_this_year" in folded:
        return "今年不办", "off"
    if orderable is True:
        return "现在能下单", "now"
    if any(token in folded for token in ("preannounce", "no_sku", "not_open", "upcoming", "coming_soon", "announced")):
        return "预告未开卖", "soon"
    if any(token in folded for token in ("cancelled", "canceled", "skipped")):
        return "今年不办", "off"
    if orderable is not False and any(token in folded for token in ("orderable", "on_sale", "orders_open", "sale_live")):
        return "现在能下单", "now"
    return "预告未开卖", "soon"

def clean_free_item(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    if as_bool(item.get("genuine")) is not True:
        return None
    provider = clean_text(item.get("provider") or item.get("name"))
    if not provider:
        return None
    type_key, type_label = classify_type(item.get("type") or item.get("kind"))
    conditions = item.get("free_conditions")
    if isinstance(conditions, str):
        conditions = {"deadline_note": conditions}
    if not isinstance(conditions, dict):
        conditions = {}
    card_required = as_bool(conditions.get("card_required"))
    specs = specs_from(item.get("specs") or item.get("config"))
    posts: list[dict[str, str]] = []
    for post in as_list(item.get("posts")):
        if isinstance(post, str):
            url = clean_url(post)
            if url:
                posts.append({"url": url, "time_beijing": "", "author": "", "role": ""})
            continue
        if not isinstance(post, dict):
            continue
        url = clean_url(post.get("url"))
        if not url:
            continue
        posts.append(
            {
                "url": url,
                "time_beijing": clean_text(post.get("time_beijing")),
                "author": clean_text(post.get("author")),
                "role": clean_text(post.get("role")),
            }
        )
    return {
        "id": clean_text(item.get("id")) or norm_compact(provider) or "vps",
        "provider": provider,
        "type": type_key,
        "type_label": type_label,
        "specs": specs,
        "free_conditions": {
            "card_required": card_required,
            "card_notes": clean_text(conditions.get("card_notes")),
            "region_limits": clean_text(conditions.get("region_limits")),
            "idle_reclaim": clean_text(conditions.get("idle_reclaim")),
            "deadline": clean_text(conditions.get("deadline")),
            "deadline_note": clean_text(conditions.get("deadline_note")),
        },
        "official_url": clean_url(item.get("official_url") or item.get("url")),
        "posts": posts,
        "notes": clean_text(item.get("notes") or item.get("note")),
    }

def clean_bf_plan(plan: Any) -> dict[str, str] | None:
    if isinstance(plan, str):
        name = clean_text(plan)
        return {"name": name} if name else None
    if not isinstance(plan, dict):
        return None
    name = clean_text(plan.get("name") or plan.get("title") or plan.get("plan") or plan.get("sku") or plan.get("display_name"))
    price = price_text(plan.get("price") or plan.get("price_as_shown") or plan.get("prices"))
    specs = clean_text(plan.get("specs"))
    if not specs and not isinstance(plan.get("config"), (dict, list)):
        specs = clean_text(plan.get("config"))
    if not specs:
        rows = specs_from(plan.get("config") if isinstance(plan.get("config"), (dict, list)) else None)
        if not rows:
            rows = []
            for key in ("cpu", "ram", "memory", "disk", "location", "bandwidth", "traffic"):
                cell = clean_text(plan.get(key))
                if cell:
                    rows.append({"label": spec_label(key), "value": cell})
        specs = config_line(rows)
    url = clean_url(plan.get("official_order_url") or plan.get("order_url") or plan.get("url"))
    if not any((name, price, specs, url)):
        return None
    out: dict[str, str] = {}
    if name:
        out["name"] = name
    if price:
        out["price"] = price
    if specs:
        out["specs"] = specs
    if url:
        out["url"] = url
    return out

def clean_official(entry: Any) -> dict[str, Any] | None:
    if not isinstance(entry, dict):
        return None
    provider = clean_text(entry.get("provider") or entry.get("name"))
    if not provider:
        return None
    status = clean_text(entry.get("status"))
    orderable = as_bool(entry.get("orderable_now"))
    label, kind = classify_status(status, orderable)
    sources: list[dict[str, str]] = []
    for src in as_list(entry.get("sources")):
        if isinstance(src, str):
            url = clean_url(src)
            if url:
                sources.append({"url": url})
            continue
        if not isinstance(src, dict):
            continue
        item: dict[str, str] = {}
        typ = clean_text(src.get("type"))
        url = clean_url(src.get("url"))
        title = clean_text(src.get("title"))
        fetched = clean_text(src.get("fetched_beijing") or src.get("time_beijing"))
        if typ:
            item["type"] = typ
        if url:
            item["url"] = url
        if title:
            item["title"] = title
        if fetched:
            item["fetched_beijing"] = fetched
        if item.get("url") or item.get("title"):
            sources.append(item)
    plans = []
    for plan in as_list(entry.get("plans")):
        cleaned = clean_bf_plan(plan)
        if cleaned:
            plans.append(cleaned)
    return {
        "provider": provider,
        "status": status,
        "status_label": label,
        "status_kind": kind,
        "orderable_now": orderable is True,
        "summary": clean_text(entry.get("summary") or entry.get("note")),
        "sources": sources,
        "sale_hub": clean_url(entry.get("sale_hub") or entry.get("sale_url")),
        "plans": plans,
    }

def clean_lead(entry: Any) -> dict[str, str] | None:
    if isinstance(entry, str):
        text = clean_text(entry)
        return {"source": text, "note": "", "url": clean_url(text)} if text else None
    if not isinstance(entry, dict):
        return None
    source = clean_text(entry.get("source") or entry.get("title") or entry.get("name"))
    note = clean_text(entry.get("note") or entry.get("summary"))
    url = clean_url(entry.get("url")) or clean_url(source)
    if not source and not note and not url:
        return None
    return {"source": source or url, "note": note, "url": url}
