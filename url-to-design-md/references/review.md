# The questionnaire — the step between a measurement and a decision

A measurement cannot approve itself. This is the step where it stops being data and becomes a
choice, and it is the only part of this skill a person has to be present for.

It has one shape: **show, then ask, one decision at a time, each with its picture.** And it can be
skipped in a single answer, which is also a decision and is written down as one.

## Why the picture is not optional

> *"`muted-foreground` on background is 2.54:1, below the 4.5 that WCAG AA asks for."*

That is a true sentence about a colour and **nobody can answer it**. The same two greys printed on
the real ground, in the real typeface, at the real size, answer themselves in a second.

So every question arrives with `scripts/render_decision.py` run on it, screenshotted, shown. Four
kinds: `contrast`, `type`, `colour`, `spacing`. They reuse the guide's own `:root` and stylesheet,
so the specimen is made of the same variables as the system — a comparison with its own styling
would be a third renderer showing a design that exists nowhere.

## The questions are derived, never written

`analyze.py#open_questions` produces them from conditions the measurement can detect:

| Condition | What is asked |
|---|---|
| a contrast pair below 4.5 | keep the source's value, or darken until it passes |
| a colour role seen on fewer than half the pages | read more pages, or accept it |
| a component marked `inferred` | point at a page that has one, or let the default stand |
| slots with no evidence | accept the framework defaults, or read more |
| a type step ≥ 56px at 390px | keep the ramp, or lighten the mobile end |
| steps that are not uniform | keep the chosen sizes, or regularise onto a ratio |
| only one colour scheme read | read the other theme, or ship one |

A run that finds none of these **says so**. An empty questionnaire is a result, not a skipped step.

Every question carries four things, and the last two are the ones that get skipped:

- **the evidence** — what was measured, where;
- **the options** — never more than two or three, each a real action;
- **a recommendation, inside the options.** One option is marked as the one to take, first in the
  list, and its description says *why*. The agent has the measurement in front of it; staying
  neutral is not impartiality, it is leaving the user to work out the one thing they cannot read off
  the screen. Where there genuinely is no preference, say so in the question — never omit it in
  silence.
- **what happens if nobody answers.** A question that quietly did something is worse than no
  question at all.

## The order

**1. Show the guide.** The file, so they can scroll it themselves, plus a screenshot of the review
band. Never a summary instead of the artefact.

**2. Offer the skip first.** Before any detail:

> *"The measurement raised N things. Shall we go through them, or straight to the DESIGN.md?"*

Taking the skip is legitimate and fast. It is not the same as reviewing, and `design-source.md`
records the difference: *"accepted without review, by the user, on <date>"* against *"reviewed"*.
An unreviewed system and an approved one must never look the same afterwards.

**3. Ask, with the picture.** Generate the decision page, screenshot it, show it, then ask. Up to
four at a time; more than that and the pictures stop being looked at.

**4. Apply, regenerate, re-verify.** Every answer either moves a value in `tokens.json` or is
recorded as accepted. After a move: re-render the guide, re-run `verify.py`, and show the result.
The loop is the point — *"lighten the headline"* → regenerate → look again — and it runs as many
times as the user wants.

For a contrast fix, use `analyze.adjust_for_contrast`: it moves lightness in OKLab and holds hue and
chroma, so the result is the same colour with less light. Darkening in sRGB turns a blue-grey into a
different colour, and the user did not ask for a different colour. Measured on the test page:
`#9ca3af` (2.54, fail) → `#707782` (4.52, AA), hue 261.3 → 259.4, chroma 0.0192 → 0.0189.

**5. Check the drift before closing.** `analyze.slop_drift(final, measured)` compares what is about
to be written with what was measured, and names anything that moved **away from the source and
towards the look AI-generated design keeps landing on** — the cream ground, the terracotta accent,
Inter as the safe face, `rounded-lg` on everything, the purple-to-blue hero.
(`design-md-to-app/references/anti-slop-fallbacks.md` owns that subject; this only watches the
drift.) Raise each one as a question like any other: it may be exactly what the user wanted, and
then the answer is recorded rather than the move being undone.

**Only drift counts.** A site that genuinely uses Inter on cream *is* that site. Flagging a value
that was measured and kept would punish an accurate measurement, which is the opposite of the job.

**6. Close.** When the user stops moving things, write the DESIGN.md and the record.

## What this step must not become

**A form.** Seven questions in a row with no pictures is a form, and a form gets answered with
whatever dismisses it fastest. If a question cannot be shown, it is not ready to be asked.

**A gate the agent walks through alone.** Every answer here is the user's. The agent may recommend —
it has the measurement — but *"I accepted the defaults on your behalf"* is not an outcome this step
has.
