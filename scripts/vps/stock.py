"""Build restock entries and match watched plans to provider catalogs."""

from __future__ import annotations

from typing import Any

from .normalize import (
    as_bool, as_list, clean_text, clean_url, config_line, hostname, norm_compact,
    norm_space, price_text, specs_from, unsafe_key,
)


SOURCE_LABELS = {
    "vpsrestock": "vpsrestock.com",
    "telegram_dmitnews": "t.me/dmitnews",
    "dmit_telegram": "t.me/dmitnews",
    "stock_bwg_la": "stock.bwg.la",
    "stock.bwg.la": "stock.bwg.la",
    "dmit_official_site": "DMIT 官网",
}

def normalize_stock(value: Any) -> str:
    if isinstance(value, bool):
        return "in_stock" if value else "out_of_stock"
    text = norm_space(value).replace(" ", "_").replace("-", "_")
    if text in {"in_stock", "instock", "available", "yes", "true", "有货"}:
        return "in_stock"
    if text in {"out_of_stock", "outofstock", "out", "sold_out", "soldout", "unavailable", "no", "false", "缺货"}:
        return "out_of_stock"
    return "out_of_stock" if text else ""

def pid_of(obj: Any) -> str:
    if not isinstance(obj, dict):
        return ""
    sources = [obj]
    config = obj.get("config")
    if isinstance(config, dict):
        sources.append(config)
    for source in sources:
        for key in ("pid", "product_id", "plan_id"):
            if unsafe_key(key):
                continue
            text = clean_text(source.get(key))
            if text and text.casefold() not in {"0", "none", "null"}:
                return text
    return ""

def order_label(url: str, explicit: str = "") -> str:
    label = clean_text(explicit)
    if label and label.casefold() not in {"official_order_url", "official_order_url_cn_mirror"}:
        return label
    host = hostname(url)
    if "bwh81.net" in host:
        return "bwh81.net"
    if "bandwagonhost.com" in host:
        return "bandwagonhost.com"
    return "官网下单"

def push_order_url(links: list[dict[str, str]], url: Any, label: str = "") -> None:
    cleaned = clean_url(url)
    if not cleaned:
        return
    if any(item.get("url") == cleaned for item in links):
        return
    links.append({"label": order_label(cleaned, label), "url": cleaned})

def order_urls_from(obj: Any) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    if not isinstance(obj, dict):
        return links
    pairs = (
        ("official_order_url", ""),
        ("official_order_url_cn_mirror", "bwh81.net"),
        ("order_url", ""),
        ("order_url_cn", "bwh81.net"),
        ("cn_mirror_url", "bwh81.net"),
        ("order_url_mirror", "bwh81.net"),
    )
    for key, label in pairs:
        if key in obj:
            push_order_url(links, obj.get(key), label)
    return links

def plan_names(plan: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    for key in ("display_name", "name", "key"):
        text = clean_text(plan.get(key))
        if text:
            found.add(norm_space(text))
            found.add(norm_compact(text))
    for alias in as_list(plan.get("aliases")):
        text = clean_text(alias)
        if text:
            found.add(norm_space(text))
            found.add(norm_compact(text))
    found.discard("")
    return found

def match_catalog(plan: dict[str, Any], catalogs: list[Any]) -> list[dict[str, Any]]:
    wanted_pid = pid_of(plan)
    wanted_names = plan_names(plan)
    matches: list[dict[str, Any]] = []
    seen: set[int] = set()
    items: list[dict[str, Any]] = []
    for catalog in catalogs:
        for item in as_list(catalog):
            if isinstance(item, dict):
                items.append(item)
    for item in items:
        item_pid = pid_of(item)
        if wanted_pid and item_pid and wanted_pid == item_pid:
            if id(item) not in seen:
                matches.append(item)
                seen.add(id(item))
    for item in items:
        if id(item) in seen:
            continue
        if wanted_names and (plan_names(item) & wanted_names):
            matches.append(item)
            seen.add(id(item))
    return matches

def clean_source_entry(key: str, value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        url = clean_url(value)
        if not url:
            return None
        return {"name": SOURCE_LABELS.get(key, hostname(url) or key), "url": url, "checked_at_beijing": ""}
    url = clean_url(value.get("url") or value.get("href"))
    name = clean_text(value.get("name") or value.get("title")) or SOURCE_LABELS.get(key, "")
    if not name and url:
        name = hostname(url)
    checked = clean_text(
        value.get("page_updated_beijing")
        or value.get("checked_at_beijing")
        or value.get("updated_at_beijing")
        or value.get("time_beijing")
    )
    latest = value.get("latest_post")
    if isinstance(latest, dict):
        post_url = clean_url(latest.get("url"))
        if post_url and not url:
            url = post_url
        post_time = clean_text(latest.get("time_beijing"))
        if post_time and not checked:
            checked = post_time
    note = clean_text(value.get("counts_as_shown") or value.get("note"))
    if not url and not name:
        return None
    entry = {"name": name or "来源", "url": url, "checked_at_beijing": checked}
    if note:
        entry["note"] = note
    return entry

def clean_sources(sources: Any) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    if isinstance(sources, dict):
        pairs = list(sources.items())
    elif isinstance(sources, list):
        pairs = [(str(index), item) for index, item in enumerate(sources)]
    else:
        return cleaned
    for key, value in pairs:
        if unsafe_key(key):
            continue
        entry = clean_source_entry(str(key), value)
        if entry:
            cleaned.append(entry)
    return cleaned

def is_limited(plan: dict[str, Any], matches: list[dict[str, Any]]) -> bool:
    flag = as_bool(plan.get("limited_edition"))
    if flag is None:
        flag = as_bool(plan.get("limited"))
    if flag is True:
        return True
    category = norm_space(plan.get("category"))
    if category in {"limited", "limited edition", "限量"}:
        return True
    for item in matches:
        if as_bool(item.get("limited_edition")) is True or as_bool(item.get("limited")) is True:
            return True
    return False

def clean_watched_plan(key: str, plan: Any, catalogs: list[Any]) -> dict[str, Any] | None:
    if isinstance(plan, str):
        plan = {"key": key, "display_name": plan}
    if not isinstance(plan, dict):
        return None
    matches = match_catalog(plan, catalogs)
    config = plan.get("config")
    if isinstance(config, str):
        config_text = clean_text(config)
        specs = specs_from(plan.get("specs"))
    else:
        specs = specs_from(config if config not in (None, "") else plan.get("specs"))
        config_text = config_line(specs)
    if not config_text:
        for item in matches:
            config_text = clean_text(item.get("specs") or item.get("config"))
            if config_text:
                break
    if not specs:
        for item in matches:
            specs = specs_from(item.get("specs") or item.get("config"))
            if specs:
                if not config_text:
                    config_text = config_line(specs)
                break
    price = price_text(plan.get("price_as_shown"))
    if not price:
        price = price_text(plan.get("price"))
    if not price:
        for item in matches:
            price = price_text(item.get("prices"))
            if not price:
                price = price_text(item.get("price") or item.get("price_as_shown"))
            if price:
                break
    links = order_urls_from(plan)
    for item in matches:
        for link in order_urls_from(item):
            push_order_url(links, link["url"], link["label"])
    display = clean_text(plan.get("display_name") or plan.get("name") or plan.get("key") or key)
    if not display and matches:
        display = clean_text(matches[0].get("name"))
    if not display:
        return None
    last = clean_text(plan.get("last_restock") or plan.get("restock_note") or plan.get("restock"))
    if not last:
        for item in matches:
            last = clean_text(item.get("restock_note") or item.get("last_restock"))
            if last:
                break
    stock = normalize_stock(plan.get("stock"))
    if not stock:
        for item in matches:
            stock = normalize_stock(item.get("stock"))
            if stock:
                break
    plan_key = clean_text(plan.get("key") or key or display)
    return {
        "key": plan_key,
        "display_name": display,
        "config": config_text,
        "specs": specs,
        "price": price,
        "stock": stock or "out_of_stock",
        "limited": is_limited(plan, matches),
        "last_restock": last,
        "order_urls": links,
    }

def plans_from(raw: Any, catalogs: list[Any]) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        items = list(raw.items())
    elif isinstance(raw, list):
        items = [(str(index), item) for index, item in enumerate(raw)]
    else:
        return plans
    for key, plan in items:
        if unsafe_key(key):
            continue
        cleaned = clean_watched_plan(str(key), plan, catalogs)
        if cleaned:
            plans.append(cleaned)
    return plans

def official_url_from_sources(sources: Any) -> str:
    if not isinstance(sources, dict):
        return ""
    for key in ("dmit_official_site", "official_site", "official", "homepage"):
        block = sources.get(key)
        if isinstance(block, dict):
            url = clean_url(block.get("url") or block.get("homepage"))
        else:
            url = clean_url(block)
        if url:
            return url
    return ""

def clean_provider(provider_id: str, name: str, block: Any, catalogs: list[Any], checked: str) -> dict[str, Any]:
    block = block if isinstance(block, dict) else {}
    sources = clean_sources(block.get("sources"))
    # The company homepage is not a stock data source.
    sources = [item for item in sources if item.get("name") not in {"DMIT 官网"}]
    return {
        "id": provider_id,
        "name": name,
        "checked_at_beijing": checked,
        "official_url": official_url_from_sources(block.get("sources")) or clean_url(block.get("official_url")),
        "sources": sources,
        "plans": plans_from(block.get("watched_plans") or block.get("plans"), catalogs),
    }

def source_notes(value: Any) -> list[str]:
    notes: list[str] = []
    for item in as_list(value):
        text = clean_text(item)
        if text and len(text) <= 180:
            notes.append(text)
    return notes
