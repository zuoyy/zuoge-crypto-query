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

Read from the API-key protected agent query endpoints with this priority:

- `GET ${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/portfolio/snapshot` for account summary, current positions, and account-level risk overview
- `GET ${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/strategy/context` only when the user explicitly asks for trading context
- `GET ${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/strategy/context/{symbol}` only when the user explicitly asks about a specific symbol

If the caller already has JSON context, summarize that directly and do not re-fetch.

Authenticate agent requests with `ZUOGE_CRYPTO_API_KEY` using either `Authorization: Bearer <ZUOGE_CRYPTO_API_KEY>` or `X-API-Key: <ZUOGE_CRYPTO_API_KEY>`. Do not use WebUI session cookies for this skill, and do not call non-`/api/v1/agent/` routes.

## Hermes Environment

After installing this skill into Hermes, configure:

```bash
export ZUOGE_CRYPTO_BASE_URL="http://127.0.0.1:18000"
export ZUOGE_CRYPTO_API_KEY="zg-6cddba3f0499fb41cb86f3bf87af8359"
```

The backend API process must set `AGENT_API_KEY` to the same value as `ZUOGE_CRYPTO_API_KEY`.

## Workflow

1. Decide whether the user wants account summary, position list, or symbol trading context.
2. If the user did not specify a symbol, fetch `${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/portfolio/snapshot` only.
3. If the user explicitly specified a symbol or asked for trading context, fetch `${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/strategy/context` or `${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/strategy/context/{symbol}`.
4. Start with [references/query-reply-quickstart.zh-CN.md](references/query-reply-quickstart.zh-CN.md).
5. Reply in Simplified Chinese.

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
