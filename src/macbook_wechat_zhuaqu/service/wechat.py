from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


GROUP_HEADER = "群聊列表（最近7天消息数）"
CONTACT_HEADER = "联系人列表（最近7天消息数）"
LINE_RE = re.compile(r"^\s*\d+\.\s+(.*?)\s+—\s+\d+条$")


def match_captured_keys_to_databases(db_salts: Dict[str, str], captured_keys: Iterable[dict]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    by_salt = {
        item.get("salt"): item.get("dk")
        for item in captured_keys
        if item.get("rounds") == 256000 and item.get("dkLen") == 32 and isinstance(item.get("dk"), str)
    }
    for db_name, salt in db_salts.items():
        dk = by_salt.get(salt)
        if dk and len(dk) == 64:
            result[db_name] = dk
    return result


def load_captured_keys(log_path: Path) -> List[dict]:
    if not log_path.exists():
        return []
    keys: List[dict] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            keys.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return keys


def parse_list_contacts_output(output: str) -> Tuple[List[str], List[str]]:
    groups: List[str] = []
    contacts: List[str] = []
    current: List[str] | None = None
    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        if GROUP_HEADER in line:
            current = groups
            continue
        if CONTACT_HEADER in line:
            current = contacts
            continue
        if current is None:
            continue
        matched = LINE_RE.match(line)
        if matched:
            current.append(matched.group(1))
    return groups, contacts


def build_focus_summary(markdown: str) -> str:
    items = [line[2:].strip() for line in markdown.splitlines() if line.startswith("- ")]
    if not items:
        return "今天没有提取到可用于生成摘要的文本消息。"
    focus = items[:3]
    return "今天的重点是：" + "；".join(focus)
