---
name: rule-authoring
description: Use when creating, editing, or debugging EDMC VKB Connector rules. It maps gameplay intent into valid rules.json entries, enforces catalog/operator constraints, and runs focused validation checks.
---

# Rule Authoring

Use this skill when a user asks to:
- Write new `rules.json` entries from gameplay behavior.
- Fix invalid rules (bad signal/operator/value/action shape).
- Refactor existing rules while preserving behavior.
- Explain why a rule does not fire.

This skill is specific to this repository and its rule engine (`src/edmcruleengine/rules_engine.py`).

## Inputs To Gather

Collect these before drafting rules:
- Trigger intent: "when should this become true?"
- Reset intent: "when should this become false?"
- Desired actions in each state (`then` vs `else`).
- Whether to preserve existing rule `id` values.
- Whether output should patch `rules.json` or return snippet only.

If intent is vague, ask for one concrete in-game example event/state for true and false paths.

## Authoring Workflow

1. Load authoritative references.
- `docs/RULES_GUIDE.md` for schema and semantics.
- `docs/SIGNALS_REFERENCE.md` and `data/signals_catalog.json` for valid signal names and enum values.
- `data/rules.json.example` for project style and action formatting.
- `src/edmcruleengine/rules_engine.py` for hard validation behavior.

2. Map intent to signals.
- Prefer stable "state" signals (for mode/state rules) over short-lived "event pulse" signals unless pulse behavior is intended.
- Use `all` for required conditions and `any` for alternatives.

3. Draft rule objects.
- Required: non-empty `title`.
- Optional with defaults: `id`, `enabled`, `when`, `then`, `else`.
- Keep one responsibility per rule unless coupling is intentional.

4. Validate syntax and behavior.
- `python -m json.tool rules.json`
- `python -m pytest test/test_rule_loading.py`
- `python -m pytest test/test_rules.py`
- If signals catalog changed, also run:
  `python scripts/validate_signal_catalog.py`

5. Return result.
- Provide exact JSON patch/snippet.
- Call out edge-trigger semantics and any initial-state effects.
- List commands run and whether they passed.

## Hard Constraints

Follow these every time:
- Conditions must be `{ "signal": "...", "op": "...", "value": ... }`.
- Use only catalog signals and operators.
- Bool signals support only `eq` and `ne`, with JSON booleans (`true`/`false`).
- Enum signals must use declared enum values.
- `in`/`nin` require list values.
- `exists` should omit `value` (or use `null`).
- `then`/`else` must be lists of non-empty action dicts.
- Action keys in this project: `vkb_set_shift`, `vkb_clear_shift`, `log`.
- Shift tokens: `Shift1`, `Shift2`, `Subshift1`..`Subshift7`.

## Common Failure Modes

- Rule never fires because one required signal is `unknown` on that event source.
- Enum typo (value not in catalog).
- Wrong operator for signal type (especially bool).
- Missing `else`, causing state to remain set after conditions clear.
- New `id` accidentally created, resetting edge state history.

For reusable examples and pattern templates, read:
`references/rule-patterns.md`.
