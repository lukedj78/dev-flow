---
name: forms
description: 'Build or edit any form in a Next.js 16 App Router app — create dialogs, edit panels, settings UIs, anything with input fields that persist to a backend — via one shared toolkit in `lib/forms/` with explicit dirty + valid Save gating, baseline reset on success, and discriminated-union error mapping. Supports two underlying form libraries chosen at project scaffold time: **TanStack Form + Zod** (default, recommended) or **react-hook-form + Zod** (opt-in alternative). Use when the user says "form", "edit panel", "create dialog", "settings page", "save button", "dirty state", or when they reach for `useState` to hold field values, raw `useForm`, hand-rolled dirty tracking, or inline `toast.success/error` on submit. Refuses to apply if `meta.json#stack.framework != "next"` (or monorepo web side) or `stack.nextjs_version != "16"` — Pages Router and pre-16 are out of scope. Not for: React Native forms (RN uses a different ecosystem — refer to RN-side tooling), search boxes that only filter without persisting (no backend write = not a form), reads of data to populate a form (use `data-fetching`), or React state that is not bound to form fields (use `state-discipline`).'
---

# forms — one toolkit, dirty-gated Save, shared error mapping

This skill governs **where** the form layer fits in a Next.js 16 App Router app: which hook, which rendering layer, which red flags. It does not teach `@tanstack/react-form` (or `react-hook-form`) itself — for the library's own API surface defer to the official docs.

The codebase exposes **one** shared toolkit at `lib/forms/` regardless of which underlying library the project picked. Hook names, rendering layer, and error contract are identical across the two — consumer code looks the same. The choice between TanStack Form (default) and react-hook-form is made once at project scaffold time, written to `meta.json#stack.forms`, and never mixed.

## When this skill applies

- The user asks for a "form", "edit panel", "create dialog", "settings page", "save button".
- Orchestrator (`dev-flow`) routes here after scaffolding a route that needs persistence.
- The user reaches for `useState` to hold field values, raw `useForm` (bypassing the toolkit), hand-rolled dirty tracking, inline `toast.success`/`toast.error` on submit, or `<form onSubmit>` that calls `fetch`/services directly.
- The user asks to **audit** a Next.js codebase against the form rules.

## Contract

This skill follows the dev-flow contract — see `references/contracts.md` (vendored copy). Key facts:

- Reads `meta.json#stack.framework`, `stack.nextjs_version`, `stack.forms`, `stack.ui`. For `framework = "monorepo"`, reads the equivalent keys under `stack.monorepo.web`.
- **Refuses to apply** if any of these is true:
  - `stack.framework ∉ {"next", "monorepo"}` — non-Next.js targets are out of scope (RN forms use a different ecosystem; refer the user to the React Native form patterns).
  - `stack.nextjs_version != "16"` — Next.js 15 and earlier have different `searchParams`, no `use(promise)` baseline, no `revalidatePath/revalidateTag` defaults. Refuse to apply rather than silently guess.
  - The project uses Pages Router (`pages/` directory exists). App Router only.
  - The project standardizes on a form library other than `tanstack-form` or `react-hook-form` (Formik, plain controlled state, etc.). Refuse to mix.
- Appends a `history` entry to `meta.json` for every scaffold or edit.
- Does **not** bump `phase` — forms live inside the implementation phase and don't gate progression.

## The Rule

**Every form goes through one shared toolkit at `lib/forms/`. Every form has an explicit Save button gated by dirty + valid state. No auto-save, no save-on-blur, no debounce. Never `useState` for field values. Never raw `useForm` (TanStack or RHF) outside the toolkit. Never inline `toast.success`/`toast.error` from a form component.**

A "form" is any UI with `<input>` / `<textarea>` / `<select>` / `<Checkbox>` / `<Switch>` / `<RadioGroup>` whose value persists to a backend (POST / PATCH / PUT). Display-only fields, search boxes that only filter, and fire-and-forget toggles that take no field state are not forms.

## Two patterns, one toolkit

| Form kind | Hook | Submit trigger | After success |
|---|---|---|---|
| **Edit** (panel, settings, inline editor) | `useEditForm` | `<Button type="submit">Save</Button>` — disabled unless `isDirty && canSubmit` | Form stays open. Hook resets baseline to the saved value so `isDirty` returns to `false`. |
| **Create** (dialog, new-record form) | `useCreateForm` | `<Button type="submit">Create</Button>` — disabled unless `canSubmit` | `onSuccess(result)` callback fires (close dialog, route, etc.). |

Both share the `<FormProvider>` + `<FormField>` rendering layer, the same Zod schema as validator, the same `mapFormError` error router, and the same `<FormActions>` button row. The differences: edit gates on `isDirty` and resets baseline after success; create closes via `onSuccess`.

## Library branching — `stack.forms`

The two libraries (TanStack Form + Zod, react-hook-form + Zod) produce **identical consumer code**. Only the toolkit implementation differs.

| `meta.json#stack.forms` | Hooks | Schema validator | Library docs |
|---|---|---|---|
| `"tanstack-form"` *(default for new projects)* | `useEditForm` + `useCreateForm` wrap `useForm` from `@tanstack/react-form` | Pass schema to `validators: { onChange, onBlur }` | https://tanstack.com/form/latest |
| `"react-hook-form"` *(opt-in for teams with strong preference)* | Same hook names; wrap `useForm` from `react-hook-form` with `zodResolver` | `zodResolver(schema)` from `@hookform/resolvers/zod` | https://react-hook-form.com |

The consumer of `useEditForm` / `useCreateForm` never imports the underlying library. They get a typed hook with `state.isDirty`, `state.isSubmitting`, `state.canSubmit`, `handleSubmit()`, `reset(value?)`, `Subscribe(...)`, and a `<form.Field>` (TanStack) or `<form.Field>` (RHF wrapper) equivalent for raw escape-hatch usage.

## Edit form pattern (manual save, dirty-gated)

```tsx
"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  FormActions,
  FormField,
  FormProvider,
  useEditForm,
} from "@/lib/forms";
import { projectsService } from "@/lib/services/projects.service";
import { type Project, ProjectSchema } from "@/lib/types/project";

export function ProjectEditPanel({ project }: { project: Project }) {
  const form = useEditForm<Project>({
    schema: ProjectSchema,
    defaultValues: project,
    save: (value, { signal }) =>
      projectsService.update(project.id, value, { signal }),
  });

  return (
    <FormProvider form={form}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void form.handleSubmit();
        }}
      >
        <FormField name="name" label="Name">
          {(field) => (
            <Input
              id={String(field.name)}
              value={String(field.value ?? "")}
              onChange={(e) => field.setValue(e.target.value)}
              onBlur={field.onBlur}
              aria-invalid={field.touched && !field.isValid}
            />
          )}
        </FormField>

        <FormField name="description" label="Description">
          {(field) => (
            <Textarea
              id={String(field.name)}
              value={String(field.value ?? "")}
              onChange={(e) => field.setValue(e.target.value)}
              onBlur={field.onBlur}
              aria-invalid={field.touched && !field.isValid}
            />
          )}
        </FormField>

        <FormActions
          submitLabel="Save"
          submittingLabel="Saving…"
          resetLabel="Reset"
        />
      </form>
    </FormProvider>
  );
}
```

**What the hook owns** (never reimplement in components):

- **Dirty tracking** — drives `state.isDirty` from a deep-equal compare of current values vs the current baseline (initial `defaultValues` on mount, then the most-recently-saved value).
- **Submit gating** — exposes `state.canSubmit = isValid && isDirty && !isSubmitting`. `<FormActions>` reads it via `form.Subscribe`.
- **Baseline reset on success** — after the `save` callback resolves, calls `form.reset(savedValue)` so the new clean state is the saved value. Editing back to the just-saved value should leave `isDirty === false`.
- **AbortController** on submit — if the user re-submits while a save is in flight, the in-flight one is aborted.
- **Error mapping** — thrown errors flow through `mapFormError`. The `save` callback **must throw on failure** — never catch.
- **Optional success/error toast** — owned by `mapFormError`; not by form components.

**What the consumer owns:**

- The `<form onSubmit>` wrapper that calls `form.handleSubmit()`.
- Wiring `aria-invalid` on inputs.
- Passing `{ signal }` straight through to the service method.

## Create form pattern

```tsx
"use client";

import { Input } from "@/components/ui/input";
import {
  FormActions,
  FormField,
  FormProvider,
  useCreateForm,
} from "@/lib/forms";
import { projectsService } from "@/lib/services/projects.service";
import {
  type ProjectCreateInput,
  ProjectCreateInputSchema,
} from "@/lib/types/project";

export function CreateProjectForm({
  onCreated,
}: {
  onCreated: (id: string) => void;
}) {
  const form = useCreateForm<ProjectCreateInput, { id: string }>({
    schema: ProjectCreateInputSchema,
    defaultValues: { name: "", description: "" },
    submit: (value, { signal }) => projectsService.create(value, { signal }),
    onSuccess: (created) => onCreated(created.id),
  });

  return (
    <FormProvider form={form}>
      <form onSubmit={(e) => { e.preventDefault(); void form.handleSubmit(); }}>
        <FormField name="name" label="Name">
          {(field) => (
            <Input
              value={String(field.value ?? "")}
              onChange={(e) => field.setValue(e.target.value)}
              onBlur={field.onBlur}
            />
          )}
        </FormField>
        <FormActions submitLabel="Create" submittingLabel="Creating…" />
      </form>
    </FormProvider>
  );
}
```

Create forms gate the submit button on `canSubmit = isValid && !isSubmitting` — dirty tracking is irrelevant for new records. Some teams still gate on `isDirty` to prevent submitting an entirely-default form; that's a per-project preference codified once in `useCreateForm`, never per-component.

## `FormActions`

The shared submit/reset button row. Reads form state reactively via `form.Subscribe` (TanStack) or `useFormState`-equivalent (RHF) so the rest of the form doesn't re-render when only `isDirty`/`isSubmitting` changes:

```tsx
<FormActions submitLabel="Save" submittingLabel="Saving…" resetLabel="Reset" />
```

For custom layout (Cancel between Reset and Save, dialog-footer docking, etc.) drop `<FormActions>` and inline the equivalent subscribe block. The skill ships the subscribe pattern in `references/form-actions.md`.

## Schemas

Schemas live in `lib/types/<entity>.ts` and are the single source of truth for form and service layer. Use Zod v4:

```ts
import * as z from "zod/v4";

export const ProjectSchema = z.object({
  id: z.string().uuid(),
  name: z.string().trim().min(1).max(120),
  description: z.string().trim().max(5000).nullable(),
});
export type Project = z.infer<typeof ProjectSchema>;

export const ProjectCreateInputSchema = ProjectSchema.omit({ id: true });
export type ProjectCreateInput = z.infer<typeof ProjectCreateInputSchema>;
```

- **Edit form** → full entity schema.
- **Create form** → dedicated input schema (`Schema.omit({ id, createdAt, … })`).
- **Partial PATCH** → `Schema.partial()` if the backend accepts any subset.

Never write a standalone TypeScript type that mirrors a schema. Always `z.infer<typeof XSchema>`.

## Unsaved-changes guard

Edit forms only persist on Save — leaving the route or closing the dialog with `isDirty === true` silently discards the user's work. Wire a guard at the boundary in `lib/forms/`:

- **Dialog/panel close**: subscribe to `form.state.isDirty`; prompt before closing (project-shaped — `confirm()`, shadcn `<AlertDialog>`, etc.).
- **Route navigation**: in App Router the pragmatic answer is a `beforeunload` for full-tab close + a custom `<Link>` wrapper for in-app nav.

The skill flags the requirement; the exact UX is project-shaped.

## Error handling

The `save` / `submit` callback **throws**. Do not catch inside it. The hook routes the thrown error through `mapFormError`:

| Error type | UI action |
|---|---|
| `SessionExpiredError` (HTTP 401) | Redirect to auth refresh route. Never toast. |
| `ForbiddenError` (HTTP 403) | Error toast — the user clicked Save expecting it to work. |
| Validation problem (HTTP 422 / RFC 7807 with `errors: { field: [...] }`) | Per-field server error set on the form + generic toast. |
| Other 4xx / 5xx | Toast the response body's `detail` or `title`. |
| Invalid response shape | Toast generic "invalid response". |
| `TypeError` / network failure | Toast generic "network error". Form stays dirty for retry. |

**Never wrap `save` / `submit` in try/catch.** Never call `toast.success` / `toast.error` from a form component. Never re-implement the discriminated-union routing inline — extend `mapFormError` if you need a new case.

On any error the hook does **not** reset baseline — `isDirty` stays `true`.

## i18n

If the project uses `next-intl` (or any other i18n library), all visible strings (labels, placeholders, button text, error messages) route through it. Never inline strings in form code. Add keys as you go. If the project has no i18n setup, flag the cost once at the top of the conversation but allow inline strings.

## Red flags / rationalizations

| Rationalization | Counter |
|---|---|
| "I just need a `useState` for one toggle." | Use `<FormField name="…">` with `<Switch>`. The form hook owns it. |
| "TanStack's `useForm` API is fine, I'll call it directly." | No. Always go through `useEditForm` / `useCreateForm` — they wire dirty tracking, baseline reset, error mapping, AbortController. Bypassing means each form re-derives the same concerns with a slightly different bug. |
| "I'll just `import { useForm } from 'react-hook-form'` directly." | Same answer — even when `stack.forms = "react-hook-form"`, the consumer-facing hook is `useEditForm` / `useCreateForm`. The underlying library is an implementation detail of `lib/forms/`. |
| "Auto-save would be nicer, I'll debounce 300ms." | No. The contract is explicit Save click. Auto-save changes the failure model (silent partial saves, race conditions) and the UX contract for the whole app. Project-wide decision, not per-component. |
| "I'll save on blur." | Same — save-on-blur is auto-save with a different trigger. |
| "I'll use the other form library here, I know it better." | The project standardizes on one. Mixing form libraries inside one app is a non-starter — toolkit, error mapping, dirty semantics all diverge. |
| "I'll track dirty state with my own `useState` of initial values." | The hook already exposes `state.isDirty`. Read it via `form.Subscribe`. |
| "Save button feels weird disabled — I'll always enable it." | A clean form has nothing to save; clicking would either no-op or POST identical data. Disabled is honest. |
| "I'll try/catch the save and toast myself." | Never. Errors flow through `mapFormError`. Catching swallows the discriminated-union routing and produces inconsistent UX. |
| "I'll show a success toast on every save." | Configure it once in `mapFormError`. Never toast from a form component. |
| "No AbortController needed — the button is disabled while submitting." | Stale requests can still resolve out-of-order if the user resets and re-submits quickly. Leave the AbortController on. |
| "I need per-field errors, I'll `safeParse` and `setState`." | The hook already runs the schema as validator. Errors surface via the field meta and render through `<FormField>`. |
| "This form is in a Server Component, I'll use Server Actions." | Forms with client-side validation, dirty tracking, and reactive submit gating are inherently client-side. Mark the leaf `"use client"` and keep the parent page a Server Component. |
| "I'll inline copy this once, i18n later." | The "later" pass touches every form. Add the key now. |

## Escape hatch — raw library `<Field>`

Drop to raw `<form.Field>` (TanStack) or `Controller` (RHF) — skipping `<FormField>` wrapping — for:

- File uploads (multipart/form-data, progress, drag-drop UI).
- Multi-step wizard navigation the form layer can't model linearly.
- Inline table-cell editors (one cell, no surrounding `<FormProvider>`).

Even when escaping `<FormField>`, **still use `useEditForm` / `useCreateForm`** and let `mapFormError` route errors. Still go through i18n. Still gate submit on dirty + valid. The escape hatch is the wrapper, not the hook contract.

## Toolkit reference

Build once per project. Lives at `lib/forms/`:

```
lib/forms/
├── index.ts                  # public re-exports
├── useEditForm.ts            # manual-save hook with dirty tracking + baseline reset
├── useCreateForm.ts          # manual-submit hook with onSuccess
├── FormProvider.tsx          # React context wrapping the form instance
├── FormField.tsx             # shadcn Field + Label + Error, render-prop API
├── FormActions.tsx           # Save + Reset buttons, gated via Subscribe
└── mapFormError.ts           # discriminated-union error → toast / per-field meta
```

For the canonical wiring of each file under both library backends (TanStack Form and react-hook-form), see `references/toolkit-tanstack.md` and `references/toolkit-rhf.md`.

To scaffold the toolkit in a fresh project run:

```bash
python3 scripts/scaffold_lib_forms.py --root <project-root>
```

The script reads `meta.json#stack.forms`, picks the matching template, writes the 7 files, runs `npx shadcn@latest add field input textarea select checkbox switch radio-group button label sonner` for the missing UI primitives, and appends a `history` entry to `meta.json`.

## Workflow

### Step 1 — verify the contract

Read `.workflow/meta.json`. Branch:

- `stack.framework = "next"` → check `stack.nextjs_version = "16"` (else refuse). Read `stack.forms`.
- `stack.framework = "monorepo"` → operate on the web side; check `stack.monorepo.web.framework = "next"` and `stack.monorepo.web.nextjs_version = "16"`. Read `stack.monorepo.web.forms`.
- Anything else → refuse politely, explain why.

If `stack.forms` is unset (legacy `meta.json` from before this skill existed), ask the user once: TanStack Form (default) or react-hook-form? Write the answer, then proceed.

### Step 2 — confirm prerequisites

Run the prereq checklist from the [Toolkit reference](#toolkit-reference) — `package.json` Next 16, shadcn configured (`components.json`), the underlying form library installed, `lib/forms/index.ts` exports the 7 surface items. If the toolkit is missing, run `scripts/scaffold_lib_forms.py` first.

### Step 3 — apply the pattern

For an **edit form**, follow the [Edit form pattern](#edit-form-pattern-manual-save-dirty-gated). For a **create form**, follow the [Create form pattern](#create-form-pattern). Both patterns are library-agnostic — the underlying TanStack/RHF binding lives in `lib/forms/`.

### Step 4 — append history

Append to `meta.json#history`:

```json
{
  "skill": "forms",
  "ran_at": "<now>",
  "outputs": ["app/(app)/projects/[id]/edit-panel.tsx", "lib/types/project.ts"],
  "phase_before": "<unchanged>",
  "phase_after": "<unchanged>"
}
```

This skill does not bump `phase`.

## Audit mode

When the user asks "audit my codebase against the forms skill" / "scan for form anti-patterns", produce a report — do not modify code. The detailed audit recipe (greps for each violation, severity rubric, report template) lives in `references/audit-recipe.md`.

The 10 violation kinds:

| Code | Violation | Severity |
|---|---|---|
| A | Mixed form libraries (both `@tanstack/react-form` and `react-hook-form` in `package.json`) | high |
| B | Raw `useForm` outside `lib/forms/` | high |
| C | `useState` bound to form-like inputs | medium |
| D | `toast.success`/`toast.error` from a form component | high |
| E | Save-on-blur / debounce / auto-save | medium |
| F | Hand-rolled dirty tracking (initial-values refs, manual diff) | medium |
| G | `<form onSubmit>` calling `fetch`/services directly (no `form.handleSubmit`) | high |
| H | Inline `AbortController` in form components | medium |
| I | Hardcoded UI strings when i18n is set up | low |
| J | `<Button type="submit">` not gated on `isDirty` (edit forms) | high |

## Sources

This skill is heavily inspired by — and extends — the `nextjs-forms` skill from **[lusentis/next-skills](https://github.com/lusentis/next-skills)** (MIT-licensed). The original targets TanStack Form + Zod only; this skill adds the `meta.json#stack.forms` branching layer so the same hook surface (`useEditForm` / `useCreateForm`) is also available on top of react-hook-form for teams that prefer it. The discriminated-union error contract, baseline-reset semantics, dirty-gating discipline, and red-flag catalog are preserved.

- Original: <https://github.com/lusentis/next-skills/tree/main/nextjs-forms>
- TanStack Form: <https://tanstack.com/form/latest>
- react-hook-form: <https://react-hook-form.com>
- Zod v4: <https://zod.dev>
- shadcn/ui `Field`: <https://ui.shadcn.com/docs/components/field>

## When in doubt

Re-read this skill, look at the most-recent existing edit form and create form in the codebase, and copy their structure. If the existing forms violate this skill, fix the new one to match the skill (not the existing forms) and flag the drift to the user.
