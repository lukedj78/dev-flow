# Audit recipe — `forms`

Run when the user asks: "audit my codebase against the forms skill", "scan for form anti-patterns", "find violations of the form rules", "/audit-forms".

**Do not modify code during the audit.** Produce a report only. Offer fixes afterwards.

---

## Step 1 — confirm scope

Run prereq checks first; if any fail, abort the audit and tell the user why.

```bash
# meta.json sanity
jq -r '.stack.framework, .stack.nextjs_version, .stack.forms' .workflow/meta.json
```

- `stack.framework` must be `"next"` or `"monorepo"` — else this skill doesn't apply.
- `stack.nextjs_version` must be `"16"` — else refuse.
- `stack.forms` should be `"tanstack-form"` or `"react-hook-form"`. If null, ask the user once.

Quick packaging checks:

```bash
# Next.js 16
jq -r '.dependencies.next' package.json

# One form library, not both
jq -r '.dependencies["@tanstack/react-form"], .dependencies["react-hook-form"]' package.json

# shadcn configured
ls components.json 2>&1

# Required shadcn primitives
ls components/ui/{field,input,textarea,select,checkbox,switch,radio-group,button,label,sonner}.tsx 2>&1

# Toolkit present
ls lib/forms/{index.ts,useEditForm.ts,useCreateForm.ts,FormProvider.tsx,FormField.tsx,FormActions.tsx,mapFormError.ts} 2>&1
```

If the toolkit is missing, that's a top-of-report finding — every downstream violation is partly caused by its absence. Run `python3 forms/scripts/scaffold_lib_forms.py --root <project>` to scaffold before fixing.

---

## Step 2 — scan for violations

Run these greps in parallel from the project root. Each maps to a rule. Use `rg` (ripgrep) where available; fall back to `grep -rn`.

### A. Mixed form libraries (HIGH)

```bash
# Both libraries in package.json
jq -r '.dependencies | to_entries | .[] | select(.key=="@tanstack/react-form" or .key=="react-hook-form") | .key' package.json

# Imports of the non-chosen library anywhere
rg -n --type=tsx --type=ts -e "from\s+['\"]react-hook-form['\"]" \
  -g '!node_modules' -g '!.next' -g '!lib/forms/**'
rg -n --type=tsx --type=ts -e "from\s+['\"]@tanstack/react-form['\"]" \
  -g '!node_modules' -g '!.next' -g '!lib/forms/**'
```

If both libraries are present, that's the first finding — flag it and ask which one wins before continuing the audit.

### B. Raw `useForm` outside the toolkit (HIGH)

```bash
# TanStack raw useForm
rg -n --type=tsx --type=ts -B1 -A2 -e "from\s+['\"]@tanstack/react-form['\"]" \
  -g '!node_modules' -g '!.next' -g '!lib/forms/**'

# RHF raw useForm
rg -n --type=tsx --type=ts -B1 -A2 -e "from\s+['\"]react-hook-form['\"]" \
  -g '!node_modules' -g '!.next' -g '!lib/forms/**'
```

Any hit outside `lib/forms/` is a violation. Consumer code should import from `@/lib/forms`.

### C. `useState` for form fields (MEDIUM)

```bash
rg -n --type=tsx -B1 -A8 -e 'useState' \
  -g '!node_modules' -g '!.next' \
  | rg -B4 -A4 -e '<Input\b' -e '<Textarea\b' -e '<Select\b' -e '<Checkbox\b' -e '<Switch\b' -e '<RadioGroup\b'
```

Open candidates by eye — `useState` can legitimately hold non-form UI state (e.g., dropdown-open) in a file that also has a form.

### D. `toast.success`/`toast.error` from a form component (HIGH)

```bash
# Files that import a form hook AND call toast directly
rg -ln --type=tsx -e 'useEditForm|useCreateForm' \
  -g '!node_modules' -g '!.next' -g '!lib/forms/**' \
  | xargs -I{} rg -lH --type=tsx -e 'toast\.(success|error)\b' {} 2>/dev/null
```

The only legitimate use of `toast` from a form component is for non-form events (e.g., a copy-to-clipboard button on the same page); confirm by eye.

### E. Save-on-blur / debounce / auto-save (MEDIUM)

```bash
rg -n --type=tsx --type=ts -B1 -A4 \
  -e 'onBlur.*save' -e 'debounce\(' -e 'setTimeout\(.*save' -e 'autosave|auto-save|autoSave' \
  -g '!node_modules' -g '!.next' -g '!lib/forms/**'
```

### F. Hand-rolled dirty tracking (MEDIUM)

```bash
rg -n --type=tsx --type=ts \
  -e 'initialValuesRef' -e 'isDirty\s*=\s*JSON\.stringify' -e 'lastSavedRef' \
  -e 'useRef\(\s*defaultValues\b' \
  -g '!node_modules' -g '!.next' -g '!lib/forms/**'
```

### G. `<form onSubmit>` calling fetch/services directly (HIGH)

```bash
rg -n --type=tsx -B1 -A8 -e '<form\s+onSubmit' \
  -g '!node_modules' -g '!.next' \
  | rg -B4 -A4 -e 'fetch\(' -e 'await\s+\w+Service\.' \
  | rg -v 'form\.handleSubmit'
```

### H. Inline `AbortController` in form components (MEDIUM)

```bash
rg -n --type=tsx -B1 -A4 -e 'new\s+AbortController\(' \
  $(rg -l --type=tsx -e 'useEditForm|useCreateForm' -g '!node_modules' -g '!.next' 2>/dev/null) 2>/dev/null \
  | rg -v 'lib/forms/'
```

### I. i18n bypass (LOW — needs eyes)

```bash
# Detect i18n setup first
rg -ln -e "from\s+['\"]next-intl['\"]" -e "from\s+['\"]react-i18next['\"]" -e "from\s+['\"]@lingui" \
  -g '!node_modules' -g '!.next' >/dev/null && \
rg -n --type=tsx -B1 -A1 -e '<FieldLabel>[^{<]' -e '<Button[^>]*>[A-Z][a-z]' \
  $(rg -l --type=tsx -e 'useEditForm|useCreateForm' -g '!node_modules' -g '!.next' 2>/dev/null) 2>/dev/null
```

### J. Save button not gated on `isDirty` (HIGH — edit forms only)

```bash
rg -n --type=tsx -B2 -A6 -e '<Button\s+type=["\x27]submit["\x27]' \
  $(rg -l --type=tsx -e 'useEditForm' -g '!node_modules' -g '!.next' 2>/dev/null) 2>/dev/null \
  | rg -v -e 'isDirty' -e '<FormActions'
```

---

## Step 3 — produce the report

Markdown report grouped by violation kind (A through J). For each finding:

- File path + line (clickable: `path/to/file.tsx:42`).
- 3–5 line excerpt of the offending code.
- Which rule it violates (link to the matching `SKILL.md` section).
- Corrected approach in one sentence.
- Severity per the table above.

Sort within each group by severity, then file path.

End with:

```
| Violation | High | Medium | Low | Total |
|---|---|---|---|---|
| A — Mixed libraries           | n | – | – | n |
| B — Raw useForm outside toolkit | n | – | – | n |
| …                              | … | … | … | … |
| Total                         | N | N | N | N |
```

…and a one-paragraph recommendation.

---

## Step 4 — recommended fix order

1. **Toolkit missing** (Step 1) → run `scripts/scaffold_lib_forms.py` first — every other fix depends on it.
2. **A** — pick one library, remove the other. Project-wide decision.
3. **B + D** — usually the same files; refactor together (raw `useForm` → toolkit hooks; inline toasts → `mapFormError`).
4. **J + E** — change UX; worth a focused PR with screenshot diff.
5. **C, F, G, H** — mechanical refactors once the toolkit is in place.
6. **I** — last, after structural fixes are in.

---

## Step 5 — offer next steps (do not execute unprompted)

1. **Build the toolkit** — if missing.
2. **Fix one violation kind across the codebase** — pick highest-volume.
3. **Fix one form at a time** — top-down through the report, one file per commit.
4. **Open a tracking issue** — convert report to a GitHub issue with checklist.

Wait for the user to choose before touching code.
