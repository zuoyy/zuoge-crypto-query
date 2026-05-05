#!/usr/bin/env python3
"""Validate money/price display rules in Chinese query reply references."""

from __future__ import annotations

import re
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]

TARGET_FILES = [
    SKILL_DIR / "references" / "query-reply-quickstart.zh-CN.md",
]

LABEL_PATTERNS = [
    re.compile(
        r"(账户权益|可用资金|总敞口|总持仓敞口|持仓均价|持仓名义价值|名义价值|未实现盈亏)[:：]\s*([^\s|`]+)"
    ),
    re.compile(r"\|\s*(均价|未实现盈亏|名义价值)\s+([^\s|`]+)"),
]

MONEY_LITERAL = re.compile(r"^-?\$[0-9]+\.[0-9]{2}$")
TIME_LABEL_PATTERN = re.compile(r"(账户快照时间|上次更新时间)[:：]\s*([^\s|`]+(?:\s+[^\s|`]+)*)")
TIME_LITERAL = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

SKIP_TOKENS = {"暂无数据"}


def should_skip(value: str) -> bool:
    return value in SKIP_TOKENS or value.startswith("{{") or value.endswith("}}")


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for pattern in LABEL_PATTERNS:
            for match in pattern.finditer(line):
                value = match.group(2)
                if should_skip(value):
                    continue
                if not MONEY_LITERAL.fullmatch(value):
                    errors.append(f"{path}:{lineno}: invalid money format `{value}` in `{line.strip()}`")
        for match in TIME_LABEL_PATTERN.finditer(line):
            value = match.group(2)
            if should_skip(value):
                continue
            if not TIME_LITERAL.fullmatch(value):
                errors.append(f"{path}:{lineno}: invalid time format `{value}` in `{line.strip()}`")
    return errors


def main() -> int:
    errors: list[str] = []
    for path in TARGET_FILES:
        errors.extend(validate_file(path))

    if errors:
        for item in errors:
            print(item, file=sys.stderr)
        return 1

    print("query display rules: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
