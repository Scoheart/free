"""Sanitize monitor values and normalize shared feed fields."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


UNSAFE_KEY_EXACT = {
    "password",
    "passwd",
    "pass",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "api_key",
    "apikey",
    "api_token",
    "credential",
    "credentials",
    "private_key",
    "email",
    "e_mail",
    "mail",
    "authorization",
    "cookie",
    "cookies",
    "session",
    "session_id",
}

EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}(?![A-Za-z0-9.\-])"
)

SECRET_RE = re.compile(
    r"(?:"
    r"\b(?:sk|pk|rk|ak|ghp|gho|github_pat)_[A-Za-z0-9_\-]{8,}"
    r"|\b(?:sk|pk|rk|ak)-[A-Za-z0-9_\-]{12,}"
    r"|\bAKIA[0-9A-Z]{16}\b"
    r"|\bBearer\s+[A-Za-z0-9._\-]{8,}"
    r"|(?:api[_-]?key|access[_-]?token|refresh[_-]?token|secret|password)\s*[:=]\s*\S+"
    r")",
    re.IGNORECASE,
)

SPEC_LABELS = {
    "cpu": "CPU",
    "vcpu": "CPU",
    "ram": "内存",
    "memory": "内存",
    "内存": "内存",
    "disk": "硬盘",
    "storage": "硬盘",
    "ssd": "硬盘",
    "硬盘": "硬盘",
    "port": "端口",
    "端口": "端口",
    "bandwidth": "带宽",
    "带宽": "带宽",
    "traffic": "流量",
    "transfer": "流量",
    "流量": "流量",
    "location": "位置",
    "region": "区域",
    "位置": "位置",
    "区域": "区域",
}

def unsafe_key(key: Any) -> bool:
    raw = str(key or "").strip()
    if not raw:
        return False
    if any(word in raw for word in ("邮箱", "密码", "密钥")):
        return True
    norm = raw.lower().replace("-", "_").replace(" ", "_")
    if norm in UNSAFE_KEY_EXACT:
        return True
    return norm.endswith(("_password", "_secret", "_token", "_email", "_apikey", "_api_key"))

def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    return []

def as_text(value: Any) -> str:
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = [as_text(item) for item in value]
        return "；".join(part for part in parts if part)
    if isinstance(value, dict):
        for key in ("summary", "note", "text", "message", "title", "time_beijing", "at"):
            if unsafe_key(key):
                continue
            text = as_text(value.get(key))
            if text:
                return text
        return ""
    return ""

def scrub(value: str) -> str:
    text = EMAIL_RE.sub("[redacted]", value)
    text = SECRET_RE.sub("[redacted]", text)
    return text

def clean_text(value: Any) -> str:
    text = scrub(as_text(value)).strip()
    if not text:
        return ""
    leftover = text.replace("[redacted]", "").strip(" ；,，")
    if not leftover:
        return ""
    return text

def clean_url(value: Any) -> str:
    text = clean_text(value)
    if not re.match(r"https?://", text, re.IGNORECASE):
        return ""
    if re.search(r"[\s<>\"']", text):
        return ""
    if EMAIL_RE.search(text) or SECRET_RE.search(text):
        return ""
    return text

def as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return None
    text = str(value).strip().lower()
    if text in {"true", "yes", "1", "required", "y"}:
        return True
    if text in {"false", "no", "0", "n"}:
        return False
    return None

def norm_space(value: Any) -> str:
    return re.sub(r"\s+", " ", as_text(value).casefold()).strip()

def norm_compact(value: Any) -> str:
    return re.sub(r"[\s\-_/]+", "", norm_space(value))

def hostname(url: str) -> str:
    match = re.match(r"https?://([^/?#]+)", url or "", re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).lower().split(":")[0].removeprefix("www.")

def parse_beijing(value: Any) -> datetime | None:
    text = clean_text(value)
    text = text.replace("（北京时间）", "").replace("(北京时间)", "").strip()
    if not text:
        return None
    candidates = [text, text.replace("T", " ")[:19]]
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
    )
    for candidate in candidates:
        for fmt in formats:
            try:
                return datetime.strptime(candidate[: len(datetime.now().strftime(fmt)) + 2], fmt)
            except ValueError:
                continue
        try:
            parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=None)
        except ValueError:
            continue
    return None

def latest_beijing(values: list[Any]) -> str:
    best_dt: datetime | None = None
    best_raw = ""
    for value in values:
        raw = clean_text(value)
        parsed = parse_beijing(raw)
        if parsed is None:
            if raw and not best_raw and best_dt is None:
                best_raw = raw
            continue
        if best_dt is None or parsed > best_dt:
            best_dt = parsed
            best_raw = raw
    return best_raw

def spec_label(key: Any) -> str:
    raw = str(key or "").strip()
    if not raw or unsafe_key(raw):
        return ""
    if raw in SPEC_LABELS:
        return SPEC_LABELS[raw]
    lowered = raw.lower()
    if lowered in SPEC_LABELS:
        return SPEC_LABELS[lowered]
    return raw

def specs_from(value: Any) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                label = clean_text(item.get("label") or item.get("name") or item.get("key"))
                cell = clean_text(item.get("value") if "value" in item else item.get("text"))
                if label or cell:
                    rows.append({"label": spec_label(label) or label, "value": cell})
            else:
                cell = clean_text(item)
                if cell:
                    rows.append({"label": "", "value": cell})
        return rows
    if isinstance(value, dict):
        for key, cell in value.items():
            label = spec_label(key)
            if not label:
                continue
            text = clean_text(cell)
            if text:
                rows.append({"label": label, "value": text})
        return rows
    text = clean_text(value)
    if text:
        rows.append({"label": "", "value": text})
    return rows

def config_line(specs: list[dict[str, str]]) -> str:
    parts: list[str] = []
    for row in specs:
        value = row.get("value") or ""
        if not value:
            continue
        label = row.get("label") or ""
        if label in {"位置", "区域"}:
            parts.append(value)
        else:
            parts.append(value)
    return " / ".join(parts)

def price_text(value: Any) -> str:
    if isinstance(value, list):
        parts = [clean_text(item) for item in value]
        return " / ".join(part for part in parts if part)
    return clean_text(value)
