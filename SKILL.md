---
name: zuoge-crypto-query
description: Use this skill when the user wants to query crypto-trader account info, current positions, or trading context in Simplified Chinese, including requests like `查下账户`, `看看持仓`, `当前有哪些仓位`, `查 BTCUSDT`, or `查 trading context`.
---

# Zuoge Crypto Query

## Overview

Use this skill when the user wants to inspect account information, current positions, or a symbol trading context in Chinese.
This skill is query-only. It does not compose or submit trade signals.

Typical requests:

- `查下账户`
- `详细看下账户信息`
- `看看当前持仓`
- `当前有哪些仓位`
- `查 BTCUSDT`
- `查 BTCUSDT 的 trading context`

## Data Source

Read from the agent query endpoints with this priority:

- `GET /api/v1/agent/account-context` for account summary, current positions, and account-level risk overview
- `GET /api/v1/agent/trading-context` only when the user explicitly asks about a specific symbol or explicitly asks for trading context

If the caller already has JSON context, summarize that directly and do not re-fetch.

## Workflow

1. Decide whether the user wants account summary, position list, or symbol trading context.
2. If the user did not specify a symbol, fetch `account-context` only.
3. If the user explicitly specified a symbol or asked for trading context, fetch `trading-context`.
3. Start with [references/query-reply-quickstart.zh-CN.md](references/query-reply-quickstart.zh-CN.md).
4. Reply in Simplified Chinese.

If the user did not specify a symbol, do not surface any symbol-specific results in the final answer.
If the user only asked for account info or account overview, do not expand the `positions` list unless they explicitly asked to see positions or a detailed account breakdown.

## Progressive Disclosure

Read only:

- [references/query-reply-quickstart.zh-CN.md](references/query-reply-quickstart.zh-CN.md)

Avoid opening signal schema, payload template, OpenAPI, or signal-generation references in this skill.

## Output Rules

- Use Simplified Chinese.
- Translate `long/short` to `多头/空头`.
- Translate `cross/isolated` to `全仓/逐仓`.
- Format money and price fields as `$1234.56` or `-$48.60`.
- Format snapshot/update times as `YYYY-MM-DD HH:MM:SS` in Beijing time; never surface raw RFC3339/ISO timestamps like `2026-05-05T04:43:03.68039Z`.
- Do not force two decimal places onto quantities, leverage, counts, or ratios.
- Use `暂无数据` for missing fields.
- When the user asks only for `账户信息 / 账户快览 / 查下账户`, reply with account-level summary only. Do not append position details, symbol drill-downs, or optional next-step menus unless the user explicitly asks.
- For this user, keep the reply minimal and direct: one compact summary plus one concise risk sentence is preferred over extra explanation.

## Maintenance

After changing query templates or examples, run:

```bash
python3 scripts/validate_query_display_rules.py
```
