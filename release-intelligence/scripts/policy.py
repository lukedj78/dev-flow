"""policy.py — who may press which button: one deterministic table, no model judgement.

    from policy import decide
    decide("deployment_rollback", risk="high", autonomy="automated")  -> "approval"

The whole capability rests on this file, so it is small, pure, and tested on its own. Three inputs,
one of four verdicts:

| verdict | meaning |
|---|---|
| `auto` | the agent may execute it now and report afterwards |
| `approval` | the agent prepares it fully and waits for the user's explicit yes |
| `recommend` | the agent describes it and does not prepare a write (advisory mode) |
| `never` | nothing in this capability executes it, in any mode |

**Two rules that no configuration can relax**, because each of them is a one-way door:

1. **A destructive database operation is never `auto`.** `release-intelligence` never drops a column,
   truncates a table or deletes production rows, whatever the autonomy mode says. The verdict is
   `approval` at best, and `references/database-migrations.md` is the procedure.
2. **Pausing and stopping are always `auto`.** Making something safer must never wait for a human who
   is asleep. This is the asymmetry that makes progressive delivery worth having: advancing needs
   evidence and often a person, retreating needs neither.

Everything else is `meta.json#release.autonomy` plus the risk level, and a project can tighten any
row through `meta.json#release.required_approvals` — tighten only. An override that would turn an
`approval` into an `auto` is ignored and reported, because a config file is not an authorisation.

Stdlib only.
"""

from __future__ import annotations

RISKS = ("low", "medium", "high", "critical")
AUTONOMY = ("disabled", "advisory", "assisted", "automated")
VERDICTS = ("auto", "approval", "recommend", "never")

#: Reading the state of the world. Always allowed — these write nothing outside `.workflow/`.
READ_ONLY = ("risk_assessment", "release_planning", "flag_proposal", "health_check", "verification")

#: Making something safer. Always `auto`: a pause that waits for approval is not a safety control.
ALWAYS_AUTO = ("rollout_pause", "rollout_abort")

#: Never automated, in any mode. The verdict for these is `approval` — they are not forbidden, they
#: are *not the agent's to decide*.
NEVER_AUTO = ("destructive_db_migration", "flag_delete", "production_data_change")

#: The automated-mode table: action -> the highest risk level at which it may still run unattended.
#: A risk above the entry needs the user. Absent from the table means `approval` at every level.
AUTO_UP_TO: dict[str, str] = {
    "flag_create": "low",
    "rollout_advance": "low",
    "flag_rollback": "medium",      # turning a flag off restores the previous behaviour: cheap to undo
    "deployment_rollback": "low",
    "cleanup_pr": "high",           # a PR is a proposal; merging it is still a person's click
}


def _rank(risk: str) -> int:
    return RISKS.index(risk) if risk in RISKS else len(RISKS) - 1  # an unknown risk reads as critical


def decide(action: str, risk: str, autonomy: str, required_approvals: dict | None = None) -> str:
    """One of VERDICTS. Never raises: an unknown action or risk resolves to the strictest sensible answer."""
    if action in READ_ONLY:
        return "auto"
    if action in ALWAYS_AUTO:
        return "auto"

    if autonomy not in AUTONOMY:
        autonomy = "advisory"  # an unreadable mode is the most cautious one, not the most permissive
    if autonomy == "disabled":
        return "never"

    verdict = "approval"
    if autonomy == "advisory":
        verdict = "recommend"
    elif autonomy == "automated" and action not in NEVER_AUTO:
        ceiling = AUTO_UP_TO.get(action)
        if ceiling is not None and _rank(risk) <= _rank(ceiling):
            verdict = "auto"

    # A project may tighten a row, never loosen it. `{"rollout_advance": "approval"}` is honoured;
    # `{"destructive_db_migration": "auto"}` is not, and `explain()` says so.
    if required_approvals:
        want = required_approvals.get(action)
        if want in VERDICTS and VERDICTS.index(want) > VERDICTS.index(verdict):
            verdict = want
    return verdict


def override_ignored(action: str, risk: str, autonomy: str, required_approvals: dict | None) -> str | None:
    """The message for an override that tried to loosen a row, or None when there is nothing to say."""
    if not required_approvals:
        return None
    want = required_approvals.get(action)
    if want is None:
        return None
    if want not in VERDICTS:
        return (f"meta.json#release.required_approvals.{action} is {want!r}, which is not one of "
                f"{', '.join(VERDICTS)} — ignored, the default applies")
    strict = decide(action, risk, autonomy, None)
    if VERDICTS.index(want) < VERDICTS.index(strict):
        return (f"meta.json#release.required_approvals.{action} asks for {want!r} where the policy says "
                f"{strict!r} — ignored. This table may only tighten: a config file is not an authorisation")
    return None


def explain(action: str, risk: str, autonomy: str, required_approvals: dict | None = None) -> str:
    verdict = decide(action, risk, autonomy, required_approvals)
    reason = {
        "auto": "the agent may do this now and report afterwards",
        "approval": "the agent prepares it and waits for the user's explicit yes",
        "recommend": "advisory mode: described, not prepared",
        "never": "release-intelligence is disabled on this project",
    }[verdict]
    extra = ""
    if action in NEVER_AUTO:
        extra = " — never automated in any mode"
    elif action in ALWAYS_AUTO:
        extra = " — making something safer never waits"
    ignored = override_ignored(action, risk, autonomy, required_approvals)
    if ignored:
        extra += f"\n  ⚠️ {ignored}"
    return f"{action} at risk {risk} in {autonomy} mode: {verdict} — {reason}{extra}"


def table(autonomy: str, required_approvals: dict | None = None) -> str:
    """The whole policy as a markdown table, for a report the user reads once per project."""
    actions = list(READ_ONLY) + list(ALWAYS_AUTO) + sorted(AUTO_UP_TO) + list(NEVER_AUTO)
    lines = [f"Autonomy mode: **{autonomy}**", "",
             "| operation | low | medium | high | critical |", "|---|---|---|---|---|"]
    for a in actions:
        cells = " | ".join(decide(a, r, autonomy, required_approvals) for r in RISKS)
        lines.append(f"| `{a}` | {cells} |")
    return "\n".join(lines)
