# dev-flow eval harness

Two things live here now, answering different questions.

- **`run_evals.py`** — property-based golden tests for the deterministic *scripts*
  that back several skills (this file).
- **[`generated-page/check.py`](./generated-page/README.md)** — sixteen mechanical
  checks over a *generated app*, asking whether the generation followed the rules the
  skill that produced it states. Different target, different failure mode, its own
  self-test; start from its README.

Property-based golden tests for the deterministic scripts that back several
dev-flow skills. Not a replacement for end-to-end review of LLM output —
that's qualitative by nature. This catches regressions in the *deterministic*
parts (k-means quantization, DESIGN.md parsing, registry building, etc.).

## Why property assertions, not snapshots

A k-means run on a real screenshot won't produce the *exact same* palette
across runs (even with seeded RNG, downstream code rounds, sorts, deduplicates).
Snapshot testing would flag a pixel-shift as a regression when the result is
semantically identical.

So we assert *properties* instead — "the palette has 4–12 colors", "a near-white
background is recognized as ≥ 90% lightness", "the same input run 3× produces
palettes within ΔE < 5 of each other". These are stable across implementation
tweaks while catching real breakage.

## Layout

```
evals/
├── README.md                          # this file
├── run_evals.py                       # the runner
├── lib/
│   └── color.py                       # ΔE, hex parsing, lightness helpers
├── <skill-name>/
│   ├── inputs/                        # raw inputs (PNGs, .md files, etc.)
│   ├── fixtures/                      # generated/canonical inputs (synthetic)
│   └── expected/
│       └── <fixture-name>.json        # property assertions
└── ...
```

## Running

```bash
# Run all evals
python3 evals/run_evals.py

# Run only one skill
python3 evals/run_evals.py --skill image-to-design-md

# Verbose (show every assertion)
python3 evals/run_evals.py --verbose

# CI mode — exit nonzero on first failure
python3 evals/run_evals.py --ci
```

## Adding a new fixture

1. Drop the input under `evals/<skill>/inputs/` (or generate it with a script
   under `evals/<skill>/fixtures/` if reproducibility matters).
2. Write `evals/<skill>/expected/<name>.json`:

   ```json
   {
     "skill": "image-to-design-md",
     "fixture": "my-screenshot",
     "input": "evals/image-to-design-md/inputs/my-screenshot.png",
     "command": "python3 image-to-design-md/scripts/quantize_palette.py {input} --k 8",
     "assertions": [
       { "type": "palette_size_between", "min": 4, "max": 12 },
       { "type": "contains_color", "hex": "#0066cc", "tolerance_de": 8 },
       { "type": "background_lightness_above", "value": 90 },
       { "type": "stable_across_runs", "runs": 3, "max_delta_e": 5 }
     ]
   }
   ```

3. Run `python3 evals/run_evals.py --skill <skill>` and iterate.

## Assertion types

| Type | Fields | Checks |
|---|---|---|
| `palette_size_between` | `min`, `max` | output palette has between min..max colors |
| `palette_size_exact` | `value` | exact size |
| `contains_color` | `hex`, `tolerance_de` (default 5) | a palette color is within ΔE ≤ tolerance of `hex` |
| `background_lightness_above` | `value` (0–100) | the most-area color has L* ≥ value |
| `background_lightness_below` | `value` (0–100) | dark-mode check |
| `no_near_white` | (none) | palette filtered correctly — no color with L* > 95 (catches Figma chrome leaks) |
| `stable_across_runs` | `runs`, `max_delta_e` | run the command N times; mean pairwise ΔE on palette ≤ threshold |
| `output_contains_yaml_key` | `key` | DESIGN.md output has the given top-level YAML key |
| `output_section_present` | `name` | DESIGN.md output has the named markdown section |

Add new types in `evals/run_evals.py:ASSERTION_HANDLERS`.

## Philosophy

- **Deterministic skills only.** Don't try to eval LLM output here — that's
  what the skill-creator's eval-viewer is for. This harness covers
  `quantize_palette.py`, `parse_design_md.py`, `build_registry.py` —
  scripts where the output is a function of the input.
- **Properties, not snapshots.** See above.
- **Synthetic fixtures over scraped ones.** Real screenshots get stale fast
  (Figma editor chrome shifts, font rendering differs across OS). Synthetic
  PNGs generated from a palette are reproducible across machines and CI.
- **Evals in CI.** Once green, keep green: GH Actions runs `--ci` on every PR.
