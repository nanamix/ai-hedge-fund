# HKUDS AI-Trader External Signals Design

Date: 2026-05-10

## Purpose

Use `HKUDS/AI-Trader` as an external opinion and signal source for the existing `ai-hedge-fund` Telegram flow alerts. This integration is not an auto-trading system and must not place orders.

The goal is to give the user another high-quality research window while preserving the existing operating rules:

- Long-only user guidance.
- No new leveraged ETF buys.
- No short or cover recommendations.
- No copy trading.
- No automatic Toss Securities order placement.
- Cash and target-band rules override all model and external-agent opinions.

## Source Project Interpretation

`HKUDS/AI-Trader` is treated as a platform-style research source with agent skills, market intelligence, signal feeds, and optional trading-oriented features.

Allowed source concepts:

- Market intelligence summaries.
- Agent opinions.
- Paper-trading style signal records.
- Structured signal metadata such as symbol, action, confidence, rationale, and risk notes.

Explicitly disallowed source concepts:

- Copy trading.
- Direct broker execution.
- Trade synchronization.
- Short or cover actions.
- Any mechanism that can create real orders.

## Integration Mode

The first integration is read-only and local-first:

1. Clone or fork `HKUDS/AI-Trader` into a separate directory.
2. Inspect its skills, API shape, signal feed, and data formats.
3. Export normalized external signals into a local JSON file under `.cache/telegram-flow-alerts/`.
4. The existing `telegram_flow_check` reads those signals and renders them as a separate section named `외부 의견`.

No AI-Trader process should be allowed to write into portfolio state, cash events, brokerage credentials, or order files.

## Normalized Signal

The local normalized signal format should be conservative and small:

```json
{
  "source": "HKUDS/AI-Trader",
  "as_of": "2026-05-10T21:30:00+09:00",
  "symbol": "SPYM",
  "action": "watch",
  "confidence": 0.62,
  "horizon": "days",
  "rationale": "External agent suggests watching for core rebuild.",
  "risk_notes": ["Do not chase after sharp rises."],
  "raw_action": "buy"
}
```

Rules:

- `raw_action` preserves the source action for audit.
- `action` is mapped into the safe local set: `watch`, `hold`, `avoid`, `review`.
- Any source `short`, `cover`, or leveraged-buy suggestion maps to `avoid`.
- Any buy-like external action maps only to `review` unless local portfolio-band and anti-FOMO rules pass.

## Alert Behavior

Telegram alerts may include external opinions, but they must be subordinate to local rules.

Example:

```text
외부 의견
- HKUDS/AI-Trader SPYM: review, confidence 0.62
  메모: 코어 재구축 후보. 단, 오늘 즉시 매수 아님.
```

If the local rules say `보류`, the external signal cannot upgrade the decision to buy.

## Error Handling

- Missing AI-Trader checkout: continue without external opinions.
- Invalid signal JSON: ignore the bad file and add a data warning.
- Stale signals older than the configured freshness window: show only a warning or omit them.
- Disallowed action found: keep it for audit but map it to `avoid`.
- Any accidental order-related file or credential request: stop and require explicit human review.

## Testing

Unit tests:

- Normalize buy-like external signals into safe local actions.
- Map `short` and `cover` into `avoid`.
- Ignore stale external signals.
- Render external opinions without changing the final local decision.

Manual verification:

- Run dry-run alert with a sample AI-Trader signal JSON.
- Confirm `외부 의견` appears.
- Confirm local decision remains `보류` or `대기` according to local rules.
- Confirm no broker credentials or order paths are touched.

## First Implementation Scope

Phase 1 should not clone or run AI-Trader automatically from the scheduler.

Phase 1 should add only:

- A local external-signal model.
- A JSON loader.
- A safe action mapper.
- Formatter support for `외부 의견`.
- Sample fixture and tests.

Forking and running the upstream project should be a separate manual step after the read-only adapter is proven.
