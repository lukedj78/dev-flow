---
name: forms
description: 'Build or edit any form in a Next.js 16 App Router app — create dialogs, edit panels, settings UIs, anything with input fields that persist to a backend — via one shared toolkit in `lib/forms/` with explicit dirty + valid Save gating, baseline reset on success, and discriminated-union error mapping. Supports two equally-supported underlying form libraries: **TanStack Form + Zod** (default when no preference is set) or **react-hook-form + Zod** (auto-detected and used as-is when already present in the project). Use when the user says "form", "edit panel", "create dialog", "settings page", "save button", "dirty state", or when they reach for `useState` to hold field values, raw `useForm`, hand-rolled dirty tracking, or inline `toast.success/error` on submit. Refuses to apply if `meta.json#stack.framework != "next"` (or monorepo web side) or `stack.nextjs_version != "16"` — Pages Router and pre-16 are out of scope. Not for: React Native forms (RN uses a different ecosystem — refer to RN-side tooling), search boxes that only filter without persisting (no backend write = not a form), reads of data to populate a form (use `data-fetching`), or React state that is not bound to form fields (use `state-discipline`).'
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

- Reads `meta.json#stack.framework`, `stack.nextjs_version`, `stack.forms`, `stack.ui`. For `framework = "monorepo"`, reads the equivalent keys under `stack.monorepo.web`. `stack.forms` picks the state library ([selection logic](#selection-logic--decide-once-up-front)); `stack.ui` picks the rendering primitives ([branching table](#rendering-primitives--stackui)) — the two are independent and both must be resolved before writing code.
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

The two libraries (TanStack Form + Zod, react-hook-form + Zod) are **equally supported** by this skill and produce **identical consumer code**. Only the toolkit implementation differs — neither is a second-class citizen.

| `meta.json#stack.forms` | Hooks | Schema validator | Library docs |
|---|---|---|---|
| `"tanstack-form"` *(default when nothing else indicates a preference)* | `useEditForm` + `useCreateForm` wrap `useForm` from `@tanstack/react-form` | Pass schema to `validators: { onChange, onBlur }` | https://tanstack.com/form/latest |
| `"react-hook-form"` *(fully supported; auto-detected when already present)* | Same hook names; wrap `useForm` from `react-hook-form` with `zodResolver` | `zodResolver(schema)` from `@hookform/resolvers/zod` | https://react-hook-form.com |

The consumer of `useEditForm` / `useCreateForm` never imports the underlying library. They get a typed hook with `state.isDirty`, `state.isSubmitting`, `state.canSubmit`, `handleSubmit()`, `reset(value?)`, `Subscribe(...)`, and a `<form.Field>` (TanStack) or `<form.Field>` (RHF wrapper) equivalent for raw escape-hatch usage.

### Selection logic — decide once, up front

Every time this skill runs, resolve `stack.forms` **before** touching any form code, in this order:

1. **`meta.json#stack.forms` is already set** (`"tanstack-form"` or `"react-hook-form"`) → use it. Never override silently, even if the codebase looks mixed — flag drift instead (see violation A in [Audit mode](#audit-mode)).
2. **Unset → auto-detect from the project.** Check, in order:
   - `react-hook-form` (or `@hookform/resolvers`) present in `package.json#dependencies` / `devDependencies`, **or** existing `import { useForm } from "react-hook-form"` / `<Controller>` usage found in the codebase → the project has already standardized on **react-hook-form**. Set `stack.forms = "react-hook-form"` and proceed.
   - `@tanstack/react-form` present in `package.json`, **or** existing `import { useForm } from "@tanstack/react-form"` usage found → the project has already standardized on **TanStack Form**. Set `stack.forms = "tanstack-form"` and proceed.
3. **Ambiguous (both detected) or absent (neither detected, greenfield project) → ask the user once.** State the default (`"tanstack-form"`) and name the alternative; write whichever answer to `meta.json#stack.forms` before scaffolding anything. Do not guess silently in either direction — greenfield with no stated preference is the *only* case where defaulting without asking is acceptable, and even then, say out loud which one you're about to use.

Write the resolved value to `meta.json#stack.forms` immediately (Step 1 of the [Workflow](#workflow)) so every subsequent run of this skill — and every other dev-flow skill — reads the same answer.

## Rendering primitives — `stack.ui`

`stack.forms` picks the state-management library; `stack.ui` (a separate, orthogonal `meta.json` key) picks what `<FormField>` and `<FormActions>` actually render. **All code samples in this skill assume `stack.ui = "shadcn"`** (`Field` / `FieldLabel` / `FieldError` / `Button`) — that assumption must be made explicit, not silently carried over to a project that picked something else.

| `meta.json#stack.ui` | `<FormField>` renders | `<FormActions>` renders | Notes |
|---|---|---|---|
| `"shadcn"` / `"base-ui"` *(default; every example above)* | shadcn `Field` + `FieldLabel` + `FieldError` (see `references/toolkit-tanstack.md` / `references/toolkit-rhf.md`) | shadcn `Button` | `"base-ui"` here still means shadcn's component set on the Base UI primitive layer — the `Field` API is the same. |
| `"mui"` | MUI `TextField` (or `FormControl` + `InputLabel` + `FormHelperText` for non-text inputs) wired to the **same field API** the hook exposes (`value`, `setValue`, `onBlur`, `touched`, `isValid`, `errors`) | MUI `Button` / `LoadingButton`, gated on the same `canSubmit`/`isDirty` booleans | The dirty + valid gating logic lives in the hook (`useEditForm`/`useCreateForm`), not in `<FormField>` — swapping shadcn primitives for MUI ones changes zero business logic. Example: `<TextField error={touched && !isValid} helperText={touched && errors[0]} label={label} value={value} onChange={(e) => setValue(e.target.value)} onBlur={onBlur} />`. |
| anything else (Chakra, Radix vanilla, …) | Not covered by this skill's reference implementations | — | Refuse to silently invent a mapping. Either ask the user which primitives to wire (then treat the result as a project-specific `FormField`/`FormActions` implementation, still behind the same hook contract), or use the raw [escape hatch](#escape-hatch--raw-library-field) until the project has one. |

When scaffolding (`scripts/scaffold_lib_forms.py`) or hand-writing `lib/forms/FormField.tsx` for a `stack.ui = "mui"` project, keep the render-prop shape identical to the shadcn version — only the JSX inside changes.

## Edit form pattern (manual save, dirty-gated)

The `save` callback calls a **Server Action** from `lib/actions/<entity>.actions.ts` — never the service layer directly. Per the `data-fetching` skill's contract, `lib/services/` is server-only code with no `"use server"` directive; a Client Component cannot import it. The Server Action re-validates with the same Zod schema, calls the service, and revalidates:

```ts
// lib/actions/projects.actions.ts
"use server";
import { revalidatePath } from "next/cache";
import { projectsService } from "@/lib/services/projects.service";
import { ProjectSchema, type Project } from "@/lib/types/project";

export async function updateProjectAction(id: string, value: Project) {
  const parsed = ProjectSchema.parse(value);
  const saved = await projectsService.update(id, parsed);
  revalidatePath(`/projects/${id}`);
  return saved;
}
```

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
import { updateProjectAction } from "@/lib/actions/projects.actions";
import { type Project, ProjectSchema } from "@/lib/types/project";

export function ProjectEditPanel({ project }: { project: Project }) {
  const form = useEditForm<Project>({
    schema: ProjectSchema,
    defaultValues: project,
    save: (value) => updateProjectAction(project.id, value),
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
- **AbortController** on submit — if the user re-submits while a save is in flight, the hook ignores the earlier call's resolution once a newer one starts. **Note**: `save`/`submit` is passed `{ signal }` for parity with a raw service call, but a Server Action **cannot accept an `AbortSignal` as an argument** — it isn't a serializable value across the server boundary and passing it will throw. When `save` wraps a Server Action (the normal case), ignore the second parameter; the hook's own bookkeeping still guards against acting on a stale response.
- **Error mapping** — thrown errors flow through `mapFormError`. The `save` callback **must throw on failure** — never catch.
- **Optional success/error toast** — owned by `mapFormError`; not by form components.

**What the consumer owns:**

- The `<form onSubmit>` wrapper that calls `form.handleSubmit()`.
- Wiring `aria-invalid` on inputs.
- Calling the entity's **Server Action** from `save`/`submit` — never the service layer, which is server-only (see `data-fetching` skill).

## Create form pattern

Same rule: `submit` calls a Server Action, not the service directly.

```ts
// lib/actions/projects.actions.ts
"use server";
import { revalidatePath } from "next/cache";
import { projectsService } from "@/lib/services/projects.service";
import {
  type ProjectCreateInput,
  ProjectCreateInputSchema,
} from "@/lib/types/project";

export async function createProjectAction(value: ProjectCreateInput) {
  const parsed = ProjectCreateInputSchema.parse(value);
  const created = await projectsService.create(parsed);
  revalidatePath("/projects");
  return created;
}
```

```tsx
"use client";

import { Input } from "@/components/ui/input";
import {
  FormActions,
  FormField,
  FormProvider,
  useCreateForm,
} from "@/lib/forms";
import { createProjectAction } from "@/lib/actions/projects.actions";
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
    submit: (value) => createProjectAction(value),
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
import * as z from "zod";

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
| "This form needs client-side validation and dirty tracking, so I'll skip Server Actions and call the service straight from the component." | Backwards. The form component is inherently client-side (mark the leaf `"use client"`, keep the parent page a Server Component) — but `save`/`submit` still **must** call a Server Action. Services are server-only per the `data-fetching` skill; a Client Component cannot import `lib/services/` at all, with or without this skill's toolkit. |
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

- `stack.framework = "next"` → check `stack.nextjs_version = "16"` (else refuse). Read `stack.forms` and `stack.ui`.
- `stack.framework = "monorepo"` → operate on the web side; check `stack.monorepo.web.framework = "next"` and `stack.monorepo.web.nextjs_version = "16"`. Read `stack.monorepo.web.forms` and `stack.monorepo.web.ui`.
- Anything else → refuse politely, explain why.

Resolve `stack.forms` per the [selection logic](#selection-logic--decide-once-up-front) above (read if set → auto-detect from the project → ask the user only if ambiguous or absent). Resolve `stack.ui` similarly by reading it directly; if unset, ask which UI library the project uses before writing `<FormField>`/`<FormActions>` code — do not assume shadcn. Write whatever is newly decided back to `meta.json` before proceeding.

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
